from django.http import JsonResponse
from api.common.utils.logger import logger


# Add Django's 404 handler
def django_404_handler(request, exception=None):
    """
    Handle Django-level 404 errors (URL route mismatch)
    """
    logger.info(f"Django 404 Handler: {request.method} {request.path}")
    response_data = {
        'success': False,
        'message': "The requested interface does not exist",
        'data': None,
        'code': 404
    }

    return JsonResponse(response_data, status=404)


def django_500_handler(request):
    """
    Handle Django-level 500 errors
    """
    logger.info(f"Django 500 Handler: {request.method} {request.path}")
    response_data = {
        'success': False,
        'message': "Internal server error",
        'data': None,
        'code': 500
    }
    return JsonResponse(response_data, status=500)
