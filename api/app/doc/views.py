import os
import uuid
from django.http import FileResponse
from urllib.parse import quote
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.views import BaseAPIView
from api.common.http.response import BaseResponse
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.doc.serializers.request import (DocTaskRequestSerializer, SingleDocRequestSerializer,
                                             MultiFileUploadRequestSerializer)
from api.app.doc.serializers.response import (MultiFileUploadResponseSerializer, DocListResponseSerializer,
                                              DocMetaSerializer)
from api.app.doc.models import Doc
from api.app.llm.models import LLMProvider, Prompt
from api.app.project.models import Project
from api.settings.config import env, BASE_DIR
from api.common.utils.logger import logger
from api.common.http.pagination import PaginationHelper
from api.common.server.mq import RabbitMQMessageQueue


class FileUploadView(BaseAPIView):
    """Upload files and return a UUID for each, to be referenced when creating a review task."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Upload files",
        operation_description="Upload one or more files. Returns a UUID per file to be used when creating a review task.",
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                name="files",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Files to upload (multi-file supported)",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="Upload successful", schema=MultiFileUploadResponseSerializer)
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = MultiFileUploadRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            result = serializer.save()
            return BaseResponse.success(result)
        return BaseResponse.error(serializer.errors)


class FileTaskView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create review task",
        operation_description="Create a document review task using previously uploaded file UUIDs.",
        request_body=DocTaskRequestSerializer,
        responses={
            201: openapi.Response(description="Task created", schema=BaseResponseSerializer),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = DocTaskRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            result = serializer.save()
            file_info_list = result['file_info']
            documents = result['documents']
            try:
                # Publish messages to the MQ queue
                queue = RabbitMQMessageQueue(
                    queue_name=env.MQ_QUEUE_NAME
                )
                all_success = True
                provider_set = LLMProvider.objects.filter(is_deleted=False, is_active=True)
                if not provider_set:
                    raise Exception("No active LLM provider found.")
                if len(provider_set) > 1:
                    raise Exception("Multiple active LLM providers found.")
                provider = provider_set.last()

                prompt_set = Prompt.objects.filter(is_deleted=False, is_active=True)
                if not prompt_set:
                    raise Exception("No active prompt found.")
                if len(prompt_set) > 1:
                    raise Exception("Multiple active prompts found.")
                prompt = prompt_set.last()

                llm_config = provider.config
                llm_config.update({"chunk_length": provider.chunk_length,
                                   "temperature": provider.temperature,
                                   "top_p": provider.top_p,
                                   "frequency_penalty": provider.frequency_penalty,
                                   "prompt": prompt.content})

                for file_info in file_info_list:
                    message_data = {
                        'message_id': str(uuid.uuid4()),
                        'file_name': file_info['file_name'],
                        'doc_id': file_info['doc_id'],
                        'file_uuid': file_info['file_uuid'],
                        'llm_config': llm_config,
                    }
                    logger.info(f"message_data:{message_data}")
                    success = queue.send_message(message_data)
                    if not success:
                        all_success = False
                        logger.error(f"Failed to publish message: doc_id={file_info['doc_id']}")
                queue.close_connection()
                if all_success:
                    return BaseResponse.success(message="Files uploaded and review tasks created.")
                else:
                    # Roll back: delete all Doc records created in this request
                    for document in documents:
                        document.delete()
                    return BaseResponse.error(message="Failed to create review tasks.")
            except Exception as e:
                logger.error(e)
                for document in documents:
                    document.delete()
        return BaseResponse.error(serializer.errors)


class RetryTaskView(BaseAPIView):
    """Re-publish an MQ message for a document whose review failed or was not processed."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Retry review task",
        operation_description="Re-publish the MQ message for a failed or unprocessed document by doc_id.",
        request_body=SingleDocRequestSerializer,
        responses={
            200: openapi.Response(description="Retry succeeded", schema=BaseResponseSerializer),
            400: openapi.Response(description="Invalid parameters"),
            404: openapi.Response(description="Document not found or access denied"),
        }
    )
    def post(self, request, *args, **kwargs):
        doc_id = request.data.get("doc_id")
        if not doc_id:
            return BaseResponse.error(message="doc_id is required.")

        try:
            user_projects = Project.objects.filter(
                Q(viewers__id=request.user.id) | Q(owner_id=request.user.id)
            )

            doc = Doc.objects.select_related("project_id").get(
                id=doc_id,
                is_deleted=False,
                project_id__in=user_projects
            )
        except Doc.DoesNotExist:
            # Superusers can retry any document; regular users are restricted to their projects
            if request.user.is_superuser:
                try:
                    doc = Doc.objects.get(id=doc_id, is_deleted=False)
                except Doc.DoesNotExist:
                    return BaseResponse.error(message="Document not found.")
            else:
                return BaseResponse.error(message="Document not found or access denied.")

        message_data = {
            "message_id": str(uuid.uuid4()),
            "file_name": doc.file_name,
            "doc_id": doc.id,
            "file_uuid": doc.file_uuid,
        }

        try:
            queue = RabbitMQMessageQueue(queue_name=env.MQ_QUEUE_NAME)
            success = queue.send_message(message_data)
            queue.close_connection()
        except Exception as e:
            logger.error(f"Failed to publish retry message: doc_id={doc_id}, error={e}")
            return BaseResponse.error(message="Failed to retry the task. Please try again later.")

        if success:
            return BaseResponse.success(message="Task retry submitted successfully.")
        else:
            logger.error(f"MQ publish returned failure: doc_id={doc_id}")
            return BaseResponse.error(message="Failed to retry the task.")


class DocDownloadView(BaseAPIView):
    """Download the original file for a document."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Download original file",
        operation_description="Download the original uploaded file by doc_id.",
        query_serializer=SingleDocRequestSerializer(),
        manual_parameters=[
            openapi.Parameter(
                name="doc_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Document ID",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="File stream"),
            400: openapi.Response(description="Invalid parameters"),
            404: openapi.Response(description="Document not found or access denied"),
        }
    )
    def get(self, request):
        doc_id = request.GET.get("doc_id")
        if not doc_id:
            return BaseResponse.error(message="doc_id is required.")

        try:
            user_projects = Project.objects.filter(
                Q(viewers__id=request.user.id) | Q(owner_id=request.user.id)
            )
            doc = Doc.objects.select_related("project_id").get(
                id=doc_id,
                is_deleted=False,
                project_id__in=user_projects
            )
        except Doc.DoesNotExist:
            # Superusers can download any document; regular users are restricted to their projects
            if request.user.is_superuser:
                try:
                    doc = Doc.objects.get(id=doc_id, is_deleted=False)
                except Doc.DoesNotExist:
                    return BaseResponse.error(message="Document not found.")
            else:
                return BaseResponse.error(message="Document not found or access denied.")

        try:
            file_path = os.path.join(BASE_DIR, 'data', 'upload', doc.file_uuid)
            logger.info(f"file_path: {file_path}")
            response = FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{quote(doc.file_name)}"'
            return response
        except Exception as e:
            logger.error(f"File download failed: doc_id={doc_id}, error={e}")
            return BaseResponse.error(message="File download failed.")


class DocListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Review history",
        operation_description="Returns all documents belonging to projects the current user has access to.",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=DocListResponseSerializer)
        }
    )
    def get(self, request):
        if request.user.is_superuser:
            # Superusers can see all documents
            q = Doc.objects.filter(is_deleted=False).select_related('project_id', 'owner')
        else:
            # Regular users see only documents in their accessible projects
            logger.info(f"user_id:{request.user.id}")
            user_id = request.user.id
            project_list = Project.objects.filter(Q(viewers__id=user_id) | Q(owner_id=user_id)).distinct()
            # Use select_related to avoid N+1 queries
            q = Doc.objects.filter(project_id__in=project_list, is_deleted=False).select_related('project_id', 'owner')
        query = request.GET.get('q', '')
        if query:
            q = q.filter(file_name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(q, request, DocMetaSerializer)


class DocDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Document detail",
        operation_description="Retrieve detailed information for a document by doc_id.",
        query_serializer=SingleDocRequestSerializer(),
        manual_parameters=[
            openapi.Parameter(
                name="doc_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Document ID",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="Document detail", schema=DocMetaSerializer),
            400: openapi.Response(description="Invalid parameters"),
            404: openapi.Response(description="Document not found or access denied"),
        }
    )
    def get(self, request):
        doc_id = request.GET.get("doc_id")
        logger.info(f"doc_id from request: {doc_id!r}")
        doc = Doc.objects.get(id=doc_id, is_deleted=False)
        serializer = DocMetaSerializer(doc)
        data = serializer.data
        # Append the file URL
        file_uuid = doc.file_uuid.split(".")[0]
        data["file_path"] = f"{env.DOMAIN_NAME}/upload/{file_uuid}.pdf"
        return BaseResponse.success(data=data)
