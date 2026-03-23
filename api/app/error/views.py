from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated

from api.app.base.http.error_response import ErrorBaseResponse
from api.app.base.views import BaseAPIView
from api.app.base.http.response import BaseResponse
from api.app.error.models import TextError, FinancialError
from api.app.error.serializers.request import ErrorListRequestSerializer
from api.app.error.serializers.response import ErrorListResponseSerializer, ErrorItemSerializer, \
    FinanceErrorItemSerializer
from api.common.utils.logger import logger


# Create your views here.
class ErrorListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="错误列表页",
        operation_description="错误列表页, 展示具体的错误信息",
        query_serializer=ErrorListRequestSerializer(),
        responses={
            200: openapi.Response(description="获取成功", schema=ErrorListResponseSerializer)
        }
    )
    def get(self, request, *args, **kwargs):
        logger.info(f"user_id:{request.user.id}")
        doc_id = request.query_params.get("doc_id")
        q = TextError.objects.filter(doc_id=doc_id, is_deleted=False)
        # 使用响应序列化器而不是请求序列化器，并设置many=True
        data = ErrorItemSerializer(q, many=True).data
        q = FinancialError.objects.filter(doc_id=doc_id, is_deleted=False, status=0)
        # 使用响应序列化器而不是请求序列化器，并设置many=True
        finance_data = FinanceErrorItemSerializer(q, many=True).data
        return ErrorBaseResponse.success(data=data,finance_data=finance_data)
