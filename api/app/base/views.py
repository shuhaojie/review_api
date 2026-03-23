from rest_framework.views import APIView
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed, PermissionDenied
from api.common.http.response import BaseResponse
from api.common.utils.logger import logger


class BaseAPIView(APIView):
    """Base APIView with unified exception handling."""

    def handle_exception(self, exc):
        """Override exception handler to return standardized error responses."""
        logger.exception(f"API exception: {str(exc)}", exc_info=True)

        if isinstance(exc, NotAuthenticated):
            return BaseResponse.error(
                message="Authentication credentials were not provided.",
                status_code=401
            )
        elif isinstance(exc, AuthenticationFailed):
            error_detail = str(exc.detail) if hasattr(exc, 'detail') else None
            if error_detail and 'token' in error_detail.lower():
                message = "Invalid or expired token. Please log in again."
            elif error_detail and 'signature' in error_detail.lower():
                message = "Token signature verification failed."
            elif error_detail and 'expired' in error_detail.lower():
                message = "Session expired. Please log in again."
            else:
                message = "Authentication failed. Please check your credentials."
            return BaseResponse.error(
                message=message,
                status_code=401
            )
        elif isinstance(exc, PermissionDenied):
            return BaseResponse.error(
                message="You do not have permission to access this resource.",
                status_code=403
            )

        return BaseResponse.error(
            message="An internal server error occurred. Please try again later.",
            status_code=500
        )

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to catch all unhandled exceptions."""
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            return self.handle_exception(exc)
