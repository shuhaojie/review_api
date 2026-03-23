from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.common.utils.token_utils import FlexibleJWTAuthentication
from api.app.doc.serializers.response import DocListResponseSerializer, DocMetaSerializer
from api.app.doc.models import Doc
from api.common.http.response import BaseResponse
from api.app.base.views import BaseAPIView
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.serializers.response import BaseResponseSerializer
from api.common.utils.logger import logger
from api.common.utils.pagination import PaginationHelper
from api.app.project.models import Project
from api.app.project.serializers.request import CreateProjectSerializer
from api.app.project.serializers.response import ProjectListResponseSerializer, ProjectSerializer


class ProjectListView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get project list",
        operation_description="Get project list",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=ProjectListResponseSerializer)
        }
    )
    def get(self, request):
        logger.info(f"username:{request.user.username}")
        # If it's an administrator, can see all projects
        if request.user.is_superuser:
            qs = Project.objects.filter(is_deleted=False)
        # If it's a non-administrator, can only see projects they can view, either created by themselves or in the visible users
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
        operation_description="Create project",
        request_body=CreateProjectSerializer,
        responses={
            201: openapi.Response(description="Creation successful", schema=BaseResponseSerializer)
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
            return BaseResponse.success(message="Project creation successful")
        return BaseResponse.error(serializer.errors)


class ProjectDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FlexibleJWTAuthentication]

    @swagger_auto_schema(
        operation_summary="Get project file list",
        operation_description="Get project file list",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=DocListResponseSerializer)
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
        operation_description="Delete project",
        responses={
            201: openapi.Response(description="Deletion successful", schema=BaseResponseSerializer)
        }
    )
    def delete(self, request, *args, **kwargs):
        logger.info(f"username:{request.user.username}")
        Project.objects.filter(id=kwargs['pk']).update(is_deleted=True)
        return BaseResponse.success(message="Deletion successful")
