import uuid
import csv
import datetime
from django.http import HttpResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.common.http.token import FlexibleJWTAuthentication
from api.common.http.response import BaseResponse
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.views import BaseAPIView
from api.app.llm.models import Prompt, LLMProvider, LLMTest, TestSample
from api.app.llm.serializers.request import (CreatePromptRequestSerializer, UpdatePromptRequestSerializer,
                                             CreateTestSampleRequestSerializer, UpdateTestSampleRequestSerializer,
                                             CreateLLMTestRequestSerializer, UpdateLLMProviderRequestSerializer)
from api.app.llm.serializers.response import (PromptListResponseSerializer, LLMProviderResponseSerializer,
                                              LLMTestReadResponseSerializer, TestSampleResponseSerializer,
                                              TestSampleDetailResponseSerializer)
from api.common.server.mq import RabbitMQMessageQueue
from api.common.utils.logger import logger
from api.common.http.pagination import PaginationHelper
from api.settings.config import env


class PromptListView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get prompt list",
        operation_description="Get prompt list",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=PromptListResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        qs = Prompt.objects.filter(is_deleted=False)
        # If it's a non-administrator, can only see projects they can view, either created by themselves or in the visible users
        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(qs, request, PromptListResponseSerializer)

    @swagger_auto_schema(
        operation_summary="Add prompt",
        operation_description="Add prompt",
        request_body=CreatePromptRequestSerializer,
        responses={
            201: openapi.Response(description="Creation successful", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        logger.info(f"username:{request.user.username}")
        serializer = CreatePromptRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(creator_id=request.user.id)
            return BaseResponse.created(message="Creation successful")
        return BaseResponse.error(serializer.errors)


class PromptDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get prompt details",
        operation_description="Get prompt details",
        responses={
            200: openapi.Response(description="Get successful", schema=PromptListResponseSerializer)
        }
    )
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if not pk:
            return BaseResponse.id_required()

        # 1. Get single item (soft delete filter)
        instance = get_object_or_404(Prompt,
                                     id=pk,
                                     is_deleted=False)
        # 2. Serialize
        serializer = PromptListResponseSerializer(instance)

        # 3. Return directly
        return BaseResponse.success(data=serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete prompt",
        operation_description="Delete prompt",
        responses={
            200: openapi.Response(description="Deletion successful", schema=BaseResponseSerializer)
        }
    )
    def delete(self, request, *args, **kwargs):
        logger.info(f"username:{request.user.username}")
        Prompt.objects.filter(id=kwargs['pk']).update(is_deleted=True)
        return BaseResponse.deleted(message="Deletion successful")

    @swagger_auto_schema(
        operation_summary="Update prompt",
        operation_description="Full/partial update",
        request_body=UpdatePromptRequestSerializer,
        responses={200: openapi.Response("Update successful", BaseResponseSerializer)}
    )
    def put(self, request, *args, **kwargs):
        return self._update(request, *args, **kwargs)

    def _update(self, request, partial=False, *args, **kwargs):
        instance = get_object_or_404(Prompt, id=kwargs['pk'], is_deleted=False)
        ser = UpdatePromptRequestSerializer(instance, data=request.data, partial=partial)
        if ser.is_valid():
            # ★ Unique activation logic
            if ser.validated_data.get('is_active') is True:
                Prompt.objects.filter(is_active=True).update(is_active=False)

            ser.save()
            return BaseResponse.modified()
        return BaseResponse.error(ser.errors)


class ProviderListView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get LLM list",
        operation_description="Get LLM list",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=LLMProviderResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        qs = LLMProvider.objects.filter(is_deleted=False)
        # If it's a non-administrator, can only see projects they can view, either created by themselves or in the visible users

        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(qs, request, LLMProviderResponseSerializer)


class ProviderDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Update LLM",
        operation_description="Full/partial update",
        request_body=UpdatePromptRequestSerializer,
        responses={200: openapi.Response("Update successful", BaseResponseSerializer)}
    )
    def put(self, request, *args, **kwargs):
        return self._update(request, *args, **kwargs)

    def _update(self, request, partial=False, *args, **kwargs):
        # 1. Get single item
        instance = get_object_or_404(
            LLMProvider,
            id=kwargs.get('pk'),
            is_deleted=False
        )

        # 2. Validate
        serializer = UpdateLLMProviderRequestSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        if not serializer.is_valid():
            # ★ Return field-level errors to frontend as-is
            return BaseResponse.error(serializer.errors, flatten=False)

        # 3. Unique activation: turn off others first, then turn on yourself
        if serializer.validated_data.get('is_active') is True:
            LLMProvider.objects \
                .filter(is_active=True) \
                .exclude(pk=instance.pk) \
                .update(is_active=False)

        # 4. Save and refresh
        instance = serializer.save()

        # 5. Return latest data
        return BaseResponse.success(message="Update successful",
                                    data=LLMProviderResponseSerializer(instance).data
                                    )


class TestListView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get LLM test history",
        operation_description="Get LLM test history",
        responses={
            200: openapi.Response(description="Get successful", schema=LLMTestReadResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        qs = LLMTest.objects.filter(is_deleted=False)
        # If it's a non-administrator, can only see projects they can view, either created by themselves or in the visible users
        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(qs, request, LLMTestReadResponseSerializer)

    @swagger_auto_schema(
        operation_summary="Run test",
        operation_description="Run test",
        request_body=CreateLLMTestRequestSerializer(),
        responses={
            201: openapi.Response(description="Test successful", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        logger.info(f"username:{request.user.username}")
        serializer = CreateLLMTestRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            # Send message to mq queue
            queue = RabbitMQMessageQueue(
                queue_name=env.MQ_QUEUE_NAME_LLM_TEST  # Only need queue name
            )
            result = serializer.save()

            llm_config = result.provider.config

            llm_config.update({"chunk_length": result.chunk_length,
                               "temperature": result.temperature,
                               "top_p": result.top_p,
                               "frequency_penalty": result.frequency_penalty,
                               "prompt": result.prompt.content})

            message_data = {
                'message_id': str(uuid.uuid4()),
                'test_id': result.id,
                'llm_config': llm_config
            }
            logger.info(f"message_data:{message_data}")
            success = queue.send_message(message_data)
            # If one message push fails, it is considered a failure
            if not success:
                all_success = False

            # Close mq queue
            queue.close_connection()

            return BaseResponse.success(message="Test successful")
        return BaseResponse.error(serializer.errors)


class ExportLLMTestView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Export LLM test history",
        operation_description="Export LLM test history as CSV file",
        responses={
            200: openapi.Response(description="Export successful", schema=openapi.Schema(
                type=openapi.TYPE_FILE,
                description="CSV file"
            ))
        }
    )
    def get(self, request):

        logger.info(f"username:{request.user.username}")
        qs = LLMTest.objects.filter(is_deleted=False)

        # Filter conditions
        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()

        # Create HTTP response object, set content type to text/csv
        response = HttpResponse(content_type='text/csv')

        # Set Content-Disposition header, specify filename
        filename = f"llm_test_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename={filename}'

        # Create CSV writer
        writer = csv.writer(response)

        # Write CSV header
        writer.writerow(['ID', 'Prompt ID', 'Prompt Name', 'Model ID', 'Model Name', 'Status',
                         'Temperature', 'Frequency Penalty', 'TopP', 'Token Length',
                         'Hit Rate', 'Precision', 'Recall', 'Review Duration',
                         'Creator ID', 'Creator Name', 'Creation Time', 'Update Time', 'Is Deleted'])

        # Write data rows
        for test in qs:
            writer.writerow([
                test.id,
                test.prompt_id,
                test.prompt.name,
                test.provider_id,
                test.provider.name,
                test.status,
                test.temperature,
                test.frequency_penalty,
                test.top_p,
                test.chunk_length,
                test.hit_rate or '',
                test.precision or '',
                test.recall or '',
                test.duration or '',
                test.creator_id,
                test.creator.username if test.creator else '',
                test.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                test.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                test.is_deleted
            ])

        return response


class TestSampleView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get LLM test files",
        operation_description="Get LLM test files",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=TestSampleResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        qs = TestSample.objects.filter(is_deleted=False)
        # If it's a non-administrator, can only see projects they can view, either created by themselves or in the visible users
        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(qs, request, TestSampleResponseSerializer)

    @swagger_auto_schema(
        operation_summary="Add LLM test file",
        operation_description="Add LLM test file",
        request_body=CreateTestSampleRequestSerializer,
        responses={
            201: openapi.Response(description="Creation successful", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        logger.info(f"username:{request.user.username}")
        serializer = CreateTestSampleRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(creator_id=request.user.id, uid=str(uuid.uuid4()))
            return BaseResponse.created(message="Creation successful")
        return BaseResponse.error(serializer.errors)


class TestSampleDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get test document details",
        operation_description="Get test document details",
        responses={
            200: openapi.Response(description="Get successful", schema=TestSampleDetailResponseSerializer)
        }
    )
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if not pk:
            return BaseResponse.id_required()

        # 1. Get single item (soft delete filter)
        instance = get_object_or_404(TestSample,
                                     id=pk,
                                     is_deleted=False)

        # 2. Serialize
        serializer = TestSampleDetailResponseSerializer(instance)

        # 3. Return directly
        return BaseResponse.success(message="Get successful", data=serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete test document",
        operation_description="Delete test document",
        responses={
            200: openapi.Response(description="Deletion successful", schema=BaseResponseSerializer)
        }
    )
    def delete(self, request, *args, **kwargs):
        logger.info(f"username:{request.user.username}")
        TestSample.objects.filter(id=kwargs['pk']).update(is_deleted=True)
        return BaseResponse.deleted(message="Deletion successful")

    @swagger_auto_schema(
        operation_summary="Update LLM",
        operation_description="Full/partial update",
        request_body=UpdateTestSampleRequestSerializer,
        responses={200: openapi.Response("Update successful", TestSampleDetailResponseSerializer)}
    )
    def put(self, request, *args, **kwargs):
        return self._update(request, *args, **kwargs)

    def _update(self, request, partial=False, *args, **kwargs):
        instance = get_object_or_404(TestSample, id=kwargs['pk'], is_deleted=False)
        serializer = UpdateTestSampleRequestSerializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            # ★ Return field-level errors to frontend as-is
            return BaseResponse.error(serializer.errors, flatten=False)
        # ★ Unique activation logic
        if serializer.validated_data.get('is_active') is True:
            LLMProvider.objects.filter(is_active=True).update(is_active=False)

        serializer.save()
        return BaseResponse.success(message="Update successful", data=TestSampleDetailResponseSerializer(instance).data)


class PromptBatchDeleteView(BaseAPIView):
    """
    Batch delete prompts
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        operation_summary="Batch delete prompts",
        operation_description="Batch delete prompts, support soft delete",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['ids'],
            properties={
                'ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='List of prompt IDs to delete'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Batch deletion successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='Status code'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Message'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                description='Number of successful deletions'),
                                'failed_ids': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                                    description='List of IDs that failed to delete'
                                )
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Parameter error",
                schema=BaseResponseSerializer
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Batch delete prompts
        """
        try:
            # 1. Get and validate parameters
            ids = request.data.get('ids', [])

            if not isinstance(ids, list):
                return BaseResponse.error(message="Parameter ids must be a list")

            if not ids:
                return BaseResponse.error(message="Please provide a list of prompt IDs to delete")

            # Validate all IDs are integers
            valid_ids = []
            invalid_ids = []

            for item in ids:
                try:
                    valid_ids.append(int(item))
                except (ValueError, TypeError):
                    invalid_ids.append(item)

            if invalid_ids:
                return BaseResponse.error(
                    message=f"The following IDs are not valid integers: {invalid_ids}",
                    data={"invalid_ids": invalid_ids}
                )

            # 2. Batch soft delete (use transaction to ensure consistency)
            with transaction.atomic():
                # Query existing IDs
                existing_ids = list(Prompt.objects.filter(
                    id__in=valid_ids,
                    is_deleted=False
                ).values_list('id', flat=True))

                # Calculate non-existing IDs
                non_existing_ids = list(set(valid_ids) - set(existing_ids))

                # Batch soft delete
                deleted_count = Prompt.objects.filter(
                    id__in=existing_ids
                ).update(is_deleted=True)

            # 3. Record operation log
            logger.info(
                f"User {request.user.username} batch deleted prompts: "
                f"Successfully deleted {deleted_count} items, "
                f"Non-existing IDs: {non_existing_ids}"
            )

            # 4. Return result
            result_data = {
                "deleted_count": deleted_count,
                "failed_ids": non_existing_ids
            }

            if non_existing_ids:
                return BaseResponse.success(
                    message=f"Successfully deleted {deleted_count} prompts, the following IDs do not exist: {non_existing_ids}",
                    data=result_data
                )
            else:
                return BaseResponse.success(
                    message=f"Successfully deleted {deleted_count} prompts",
                    data=result_data
                )

        except Exception as e:
            logger.error(f"Batch delete prompts failed: {str(e)}")
            return BaseResponse.error(message=f"Batch deletion failed: {str(e)}")


class SetDefaultView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Set as system default parameters",
        operation_description="Set as system default parameters",
        responses={
            200: openapi.Response(description="Setting successful", schema=BaseResponseSerializer)
        }
    )
    def post(self, request, pk):
        # First set all test system defaults to False
        LLMTest.objects.filter(system_default=True).update(system_default=False)
        # Then set the current specified test as system default
        llm_test_set = LLMTest.objects.filter(id=pk)
        if not llm_test_set:
            raise Exception("No LLM test history found")
        if len(llm_test_set) > 1:
            raise Exception("Multiple LLM test histories found")
        llm_test = llm_test_set.last()
        llm_test.system_default = True
        llm_test.save()

        LLMProvider.objects.filter(is_active=True).update(is_active=False)
        provider = llm_test.provider
        provider.temperature = llm_test.temperature
        provider.top_p = llm_test.top_p
        provider.frequency_penalty = llm_test.frequency_penalty
        provider.chunk_length = llm_test.chunk_length
        provider.is_active = True
        provider.save()

        Prompt.objects.filter(is_active=True).update(is_active=False)
        prompt = llm_test.prompt
        prompt.is_active = True
        prompt.save()

        return BaseResponse.success(message="Setting successful")