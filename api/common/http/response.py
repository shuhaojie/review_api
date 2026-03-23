from rest_framework.response import Response
from rest_framework import status


class BaseResponse:
    """DRF base response class"""

    @staticmethod
    def success(data=None, message="OK", status_code=status.HTTP_200_OK, **kwargs):
        """Success response"""
        response_data = {
            'success': True,
            'message': message,
            'data': data,
            'code': status_code
        }
        response_data.update(kwargs)
        return Response(response_data, status=status_code)

    @staticmethod
    def error(message="Request failed", data=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        """Error response"""
        if isinstance(message, str):
            pass
        # If a DRF errors dict/list is given, flatten it to a single string
        elif isinstance(message, dict):
            message = BaseResponse._flatten(message)
        elif isinstance(message, list):
            message = message[0] if message else 'Invalid parameters'
        response_data = {
            'success': False,
            'message': message,
            'data': data,
            'code': status_code
        }
        response_data.update(kwargs)
        return Response(response_data, status=status_code)

    # Common shortcut methods
    @staticmethod
    def created(data=None, message="Created successfully", **kwargs):
        return BaseResponse.success(data, message, status.HTTP_201_CREATED, **kwargs)

    @staticmethod
    def deleted(data=None, message="Deleted successfully", **kwargs):
        return BaseResponse.success(data, message, status.HTTP_200_OK, **kwargs)

    @staticmethod
    def modified(data=None, message="Updated successfully", **kwargs):
        return BaseResponse.success(data, message, status.HTTP_200_OK, **kwargs)

    @staticmethod
    def id_required(message="ID is required", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)

    @staticmethod
    def not_found(message="Resource not found", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_404_NOT_FOUND, **kwargs)

    @staticmethod
    def unauthorized(message="Unauthorized", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_401_UNAUTHORIZED, **kwargs)

    @staticmethod
    def forbidden(message="Forbidden", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_403_FORBIDDEN, **kwargs)

    @staticmethod
    def bad_request(message="Bad request", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)

    @staticmethod
    def server_error(message="Internal server error", **kwargs):
        return BaseResponse.error(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, **kwargs)

    @staticmethod
    def _flatten(err_dict):
        for field, msgs in err_dict.items():
            msg = "(" + field + "): " + msgs[0] if isinstance(msgs, list) else str(msgs)
            return msg
        return 'Validation failed'
