from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from api.common.http.token import FlexibleJWTAuthentication
from api.app.doc.serializers.response import DocListResponseSerializer, DocMetaSerializer
from api.app.doc.models import Doc
from api.common.http.response import BaseResponse
from api.app.base.views import BaseAPIView
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.serializers.response import BaseResponseSerializer
from api.common.utils.logger import logger
from api.common.http.pagination import PaginationHelper
from api.app.project.models import Project
from api.app.project.serializers.request import CreateProjectSerializer
from api.app.project.serializers.response import ProjectListResponseSerializer, ProjectSerializer


class ProjectListView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="List projects",
        operation_description="Return a paginated list of all projects accessible to the current user.",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=ProjectListResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        # Superusers see all projects; regular users see only projects they own or are viewers of
        if request.user.is_superuser:
            qs = Project.objects.filter(is_deleted=False)
        else:
            qs = Project.objects.filter(
                Q(owner=request.user) | Q(viewers=request.user),
                is_deleted=False
            ).distinct()
        query = request.GET.get('q')
        if query:
            qs = qs.filter(name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(qs, request, ProjectSerializer)

    @swagger_auto_schema(
        operation_summary="Create project",
        operation_description="Create a new project and assign viewer permissions.",
        request_body=CreateProjectSerializer,
        responses={
            201: openapi.Response(description="Created successfully", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        logger.info(f"username:{request.user.username}")
        serializer = CreateProjectSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return BaseResponse.created(message="Project created successfully.")
        return BaseResponse.error(serializer.errors)


class ProjectDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="List project documents",
        operation_description="Return a paginated list of all documents belonging to the specified project.",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=DocListResponseSerializer)
        }
    )
    def get(self, request, *args, **kwargs):
        if 'pk' not in kwargs:
            return BaseResponse.id_required()
        q = Doc.objects.filter(is_deleted=False, project_id=kwargs['pk'])
        query = request.GET.get('q')
        if query:
            q = q.filter(file_name__icontains=query).distinct()
        return PaginationHelper.paginate_queryset(q, request, DocMetaSerializer)

    @swagger_auto_schema(
        operation_summary="Delete project",
        operation_description="Soft-delete the specified project.",
        responses={
            200: openapi.Response(description="Deleted successfully", schema=BaseResponseSerializer)
        }
    )
    def delete(self, request, *args, **kwargs):
        logger.info(f"username:{request.user.username}")
        Project.objects.filter(id=kwargs['pk']).update(is_deleted=True)
        return BaseResponse.deleted(message="Project deleted successfully.")
