import hashlib
import json
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status

# How long (seconds) a request fingerprint is retained to detect duplicates.
IDEMPOTENCY_WINDOW = 5

_MUTATING_METHODS = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})


class IdempotencyMiddleware:
    """
    Rejects identical mutating requests that arrive within IDEMPOTENCY_WINDOW seconds.

    Fingerprint = SHA-256( method + path + identity + body )
    - identity: Authorization header value, falling back to the client IP.
    - Multipart requests (file uploads) are exempt because the binary body is not
      deterministic and upload operations are inherently non-idempotent in a
      different sense (handled at the application level).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in _MUTATING_METHODS and not self._is_multipart(request):
            fingerprint = self._fingerprint(request)
            cache_key = f'idem_{fingerprint}'
            if cache.get(cache_key):
                return self._duplicate_response()
            cache.set(cache_key, 1, IDEMPOTENCY_WINDOW)

        return self.get_response(request)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_multipart(request):
        content_type = request.META.get('CONTENT_TYPE', '')
        return content_type.startswith('multipart/')

    @staticmethod
    def _fingerprint(request):
        identity = request.META.get('HTTP_AUTHORIZATION', '') or _client_ip(request)
        raw = f'{request.method}:{request.path}:{identity}:{request.body.decode("utf-8", errors="replace")}'
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @staticmethod
    def _duplicate_response():
        body = json.dumps({
            'success': False,
            'code': status.HTTP_429_TOO_MANY_REQUESTS,
            'message': 'Duplicate request. Please wait a moment before retrying.',
            'data': None,
        })
        return JsonResponse(
            json.loads(body),
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )


def _client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
