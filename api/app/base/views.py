from rest_framework.views import APIView
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed, PermissionDenied
from api.app.base.http.response import BaseResponse
from api.common.utils.logger import logger


class BaseAPIView(APIView):
    """自定义基础APIView，提供异常兜底"""

    def handle_exception(self, exc):
        """重写异常处理方法"""
        # 记录异常日志
        logger.exception(f"API异常: {str(exc)}", exc_info=True)

        if isinstance(exc, NotAuthenticated):
            # 认证凭证未提供或无效
            return BaseResponse.error(
                message="请先登录或提供认证凭证",
                status_code=401
            )
        elif isinstance(exc, AuthenticationFailed):
            error_detail = str(exc.detail) if hasattr(exc, 'detail') else None
            # 根据错误详情提供更具体的消息
            if error_detail and 'token' in error_detail.lower():
                message = "token无效或已过期，请重新登录"
            elif error_detail and 'signature' in error_detail.lower():
                message = "签名验证失败"
            elif error_detail and 'expired' in error_detail.lower():
                message = "登录已过期，请重新登录"
            else:
                message = "认证失败，请检查凭证是否正确"
            # 认证失败（如用户名密码错误）
            return BaseResponse.error(
                message=message,
                status_code=401
            )
        elif isinstance(exc, PermissionDenied):
            # 权限不足
            return BaseResponse.error(
                message="权限不足，无法访问此资源",
                status_code=403
            )

        # 返回统一的错误响应
        return BaseResponse.error(
            message="系统异常，请稍后重试",
            status_code=500
        )

    def dispatch(self, request, *args, **kwargs):
        """重写dispatch方法，捕获所有异常"""
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            return self.handle_exception(exc)