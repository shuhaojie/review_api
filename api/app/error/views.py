from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated

from api.app.base.views import BaseAPIView
from api.common.http.response import BaseResponse
from api.app.error.models import TextError, FinancialError
from api.app.error.serializers.request import ErrorListRequestSerializer
from api.app.error.serializers.response import ErrorListResponseSerializer, ErrorItemSerializer, \
    FinanceErrorItemSerializer
from api.common.utils.logger import logger


# Create your views here.
class ErrorListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Review errors",
        operation_description="List all text and financial errors for a given document.",
        query_serializer=ErrorListRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=ErrorListResponseSerializer)
        }
    )
    def get(self, request, *args, **kwargs):
        logger.info(f"user_id:{request.user.id}")
        doc_id = request.query_params.get("doc_id")
        q = TextError.objects.filter(doc_id=doc_id, is_deleted=False)
        data = ErrorItemSerializer(q, many=True).data
        q = FinancialError.objects.filter(doc_id=doc_id, is_deleted=False, status=0)
        finance_data = FinanceErrorItemSerializer(q, many=True).data
        return BaseResponse.success(data=data, finance_data=finance_data)
