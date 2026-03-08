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
from api.app.base.http.response import BaseResponse
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.doc.serializers.request import (DocTaskRequestSerializer, SingleDocRequestSerializer,
                                             MultiFileUploadRequestSerializer)
from api.app.doc.serializers.response import (MultiFileUploadResponseSerializer, DocListResponseSerializer,
                                              DocMetaSerializer)
from api.app.doc.models import Doc
from api.app.llm.models import LLMProvider, Prompt
from api.app.project.models import Project
from env import env, BASE_DIR
from api.common.utils.logger import logger
from api.common.utils.pagination import PaginationHelper
from api.common.server.mq_server import RabbitMQMessageQueue


class FileUploadView(BaseAPIView):
    """文件上传接口, 将文件保存下来, 并返回一个uuid给前端"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="文件上传",
        operation_description="文件上传，返回uuid，在任务创建接口将uuid再传过来",
        consumes=["multipart/form-data"],  # 告诉 Swagger 这是文件表单上传
        manual_parameters=[
            # Header 参数
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
            openapi.Parameter(
                name="files",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="文件列表（支持多文件上传）",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="创建成功", schema=MultiFileUploadResponseSerializer)
        }
    )
    def post(self, request, *args, **kwargs):
        # 将 request 传递给 serializer 的 context
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
        operation_summary="创建任务",
        operation_description="创建上传任务",
        request_body=DocTaskRequestSerializer,
        manual_parameters=[
            # Header 参数
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
        ],
        responses={
            201: openapi.Response(description="创建成功", schema=BaseResponseSerializer),
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
                # 发送消息到mq队列
                queue = RabbitMQMessageQueue(
                    queue_name=env.MQ_QUEUE_NAME  # 只需要队列名称
                )
                all_success = True
                provider_set = LLMProvider.objects.filter(is_deleted=False, is_active=True)
                if not provider_set:
                    raise Exception("没有可使用大模型")
                if len(provider_set) > 1:
                    raise Exception("找到多个大模型")
                provider = provider_set.last()

                prompt_set = Prompt.objects.filter(is_deleted=False, is_active=True)
                if not prompt_set:
                    raise Exception("没有可使用提示词")
                if len(prompt_set) > 1:
                    raise Exception("找到多个提示词")
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
                    # 有一个消息推送失败, 即视为失败
                    if not success:
                        all_success = False
                        logger.error(f"发送消息失败: doc_id={file_info['doc_id']}")
                # 关闭mq队列
                queue.close_connection()
                if all_success:
                    return BaseResponse.success(message="文件上传成功")
                else:
                    # 如果失败, 需要将Doc表的相关数据全部删掉
                    for document in documents:
                        document.delete()
                    return BaseResponse.error(message="文件上传失败")
            except Exception as e:
                logger.error(e)
                # 如果失败, 需要将Doc表的相关数据全部删掉
                for document in documents:
                    document.delete()
        return BaseResponse.error(serializer.errors)


class RetryTaskView(BaseAPIView):
    """任务重试接口：针对上传失败或处理失败的文档重新推送 MQ 消息"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="任务重试",
        operation_description="传入 doc_id，重新将对应文档信息推送至 MQ，实现失败任务重试",
        request_body=SingleDocRequestSerializer,
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="重试成功", schema=BaseResponseSerializer),
            400: openapi.Response(description="参数错误"),
            404: openapi.Response(description="文档不存在或无权访问"),
        }
    )
    def post(self, request, *args, **kwargs):
        doc_id = request.data.get("doc_id")
        if not doc_id:
            return BaseResponse.error(message="缺少 doc_id 参数")

        # 校验文档是否存在且属于用户有权限的项目
        try:
            # 获取用户有权限的所有项目
            user_projects = Project.objects.filter(
                Q(viewers__id=request.user.id) | Q(owner_id=request.user.id)
            )

            doc = Doc.objects.select_related("project_id").get(
                id=doc_id,
                is_deleted=False,
                project_id__in=user_projects
            )
        except Doc.DoesNotExist:
            # 管理员可重试所有文档，普通用户只能重试有权限的
            if request.user.is_superuser:
                try:
                    doc = Doc.objects.get(id=doc_id, is_deleted=False)
                except Doc.DoesNotExist:
                    return BaseResponse.error(message="文档不存在")
            else:
                return BaseResponse.error(message="文档不存在或无权限重试")

        # 组装消息体
        message_data = {
            "message_id": str(uuid.uuid4()),
            "file_name": doc.file_name,
            "doc_id": doc.id,
            "file_uuid": doc.file_uuid,
        }

        # 推送 MQ
        try:
            queue = RabbitMQMessageQueue(queue_name=env.MQ_QUEUE_NAME)
            success = queue.send_message(message_data)
            queue.close_connection()
        except Exception as e:
            logger.error(f"任务重试推送 MQ 失败: doc_id={doc_id}, error={e}")
            return BaseResponse.error(message="任务重试失败，请稍后重试")

        if success:
            return BaseResponse.success(message="任务重试成功")
        else:
            logger.error(f"任务重试推送 MQ 返回失败: doc_id={doc_id}")
            return BaseResponse.error(message="任务重试失败")


class DocDownloadView(BaseAPIView):
    """下载文件原文件接口"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="下载原文件",
        operation_description="根据 doc_id 下载对应的原始文件",
        query_serializer=SingleDocRequestSerializer(),
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
            openapi.Parameter(
                name="doc_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="文档 ID",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="文件流"),
            400: openapi.Response(description="参数错误"),
            404: openapi.Response(description="文档不存在或无权限"),
        }
    )
    def get(self, request):
        doc_id = request.GET.get("doc_id")
        if not doc_id:
            return BaseResponse.error(message="缺少 doc_id 参数")

        # 校验文档是否存在且用户有权限
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
            # 管理员可下载所有文档，普通用户只能下载有权限的
            if request.user.is_superuser:
                try:
                    doc = Doc.objects.get(id=doc_id, is_deleted=False)
                except Doc.DoesNotExist:
                    return BaseResponse.error(message="文档不存在")
            else:
                return BaseResponse.error(message="文档不存在或无权限下载")

        # 读取文件并返回文件流
        try:
            # 构建正确的文件路径
            file_path = os.path.join(BASE_DIR, 'api/upload/data', doc.file_uuid)
            logger.info(f"file_path: {file_path}")
            # 使用FileResponse，它会自动处理文件名编码和内容类型
            response = FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
            # 正确设置Content-Disposition
            response['Content-Disposition'] = f'attachment; filename="{quote(doc.file_name)}"'
            return response
        except Exception as e:
            logger.error(f"下载文件失败: doc_id={doc_id}, error={e}")
            return BaseResponse.error(message="文件下载失败")


class DocListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="审核历史",
        operation_description="用户所在的项目的文件，都可以看到",
        query_serializer=BaseGetRequestSerializer(),
        manual_parameters=[
            # Header 参数
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="获取成功", schema=DocListResponseSerializer)
        }
    )
    def get(self, request):
        # 首先检查用户是否为管理员
        if request.user.is_superuser:
            # 管理员可以查看所有文档
            q = Doc.objects.filter(is_deleted=False).select_related('project_id', 'owner')
        else:
            # 非管理员只能查看其有权限的项目中的文档
            logger.info(f"user_id:{request.user.id}")
            user_id = request.user.id
            project_list = Project.objects.filter(Q(viewers__id=user_id) | Q(owner_id=user_id)).distinct()
            # 使用select_related预取关联对象，避免N+1查询问题
            q = Doc.objects.filter(project_id__in=project_list, is_deleted=False).select_related('project_id', 'owner')
        # 获取搜索参数
        query = request.GET.get('q', '')
        if query:
            q = q.filter(file_name__icontains=query).distinct()
        # 帮忙补充代码
        return PaginationHelper.paginate_queryset(q, request, DocMetaSerializer)


class DocDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="文件详情",
        operation_description="根据 doc_id 获取文件详情",
        query_serializer=SingleDocRequestSerializer(),
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="Bearer token 格式: Bearer {token}, 通过user/login获取 jwt token",
                required=True,
            ),
            openapi.Parameter(
                name="doc_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="文档 ID",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="文件详情", schema=DocMetaSerializer),
            400: openapi.Response(description="参数错误"),
            404: openapi.Response(description="文档不存在或无权限"),
        }
    )
    def get(self, request):
        doc_id = request.GET.get("doc_id")
        logger.info(f"doc_id from request: {doc_id!r}")
        doc = Doc.objects.get(id=doc_id, is_deleted=False)
        serializer = DocMetaSerializer(doc)
        data = serializer.data
        # 添加文件路径
        file_uuid = doc.file_uuid.split(".")[0]
        data["file_path"] = f"{env.DOMAIN_NAME}/upload/{file_uuid}.pdf"
        return BaseResponse.success(data=data)
