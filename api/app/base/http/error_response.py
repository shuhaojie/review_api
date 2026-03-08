# utils/drf_response.py
from rest_framework.response import Response
from rest_framework import status

from api.app.base.http.response import BaseResponse


class ErrorBaseResponse(BaseResponse):
    """DRF 基础响应类"""

    @staticmethod
    def success(data=None,finance_data = None, message="操作成功", status_code=status.HTTP_200_OK, **kwargs):
        """成功响应"""
        response_data = {
            'success': True,
            'message': message,
            'data': data,
            'finance_data':finance_data,
            'code': status_code
        }
        # 添加额外的关键字参数
        response_data.update(kwargs)
        return Response(response_data, status=status_code)

