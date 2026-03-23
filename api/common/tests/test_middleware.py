from django.core.cache import cache
from django.test import override_settings, TestCase
from django.test import RequestFactory
from rest_framework import status

from api.common.middleware import IdempotencyMiddleware, IDEMPOTENCY_WINDOW

_LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

_DUMMY_VIEW = lambda request: __import__('django.http', fromlist=['HttpResponse']).HttpResponse('ok', status=200)


@override_settings(CACHES=_LOCMEM_CACHE)
class IdempotencyMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = IdempotencyMiddleware(_DUMMY_VIEW)

    def tearDown(self):
        cache.clear()

    # ------------------------------------------------------------------ #
    # Helper                                                               #
    # ------------------------------------------------------------------ #

    def _post(self, path='/', body='{"a":1}', auth='Bearer token123', **kwargs):
        req = self.factory.post(
            path,
            data=body,
            content_type='application/json',
            HTTP_AUTHORIZATION=auth,
            **kwargs,
        )
        return self.middleware(req)

    # ------------------------------------------------------------------ #
    # Happy path                                                           #
    # ------------------------------------------------------------------ #

    def test_first_request_passes(self):
        """The first request in a window should always go through."""
        resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_second_identical_request_is_rejected(self):
        """An identical second request within the window should return 429."""
        self._post()
        resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rejected_response_body(self):
        """429 response must follow the BaseResponse envelope format."""
        import json
        self._post()
        resp = self._post()
        data = json.loads(resp.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('message', data)
        self.assertIsNone(data['data'])

    # ------------------------------------------------------------------ #
    # Different fingerprints are independent                               #
    # ------------------------------------------------------------------ #

    def test_different_body_is_allowed(self):
        """A request with a different body must not be blocked."""
        self._post(body='{"a":1}')
        resp = self._post(body='{"a":2}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_different_path_is_allowed(self):
        """Requests to different paths are independent."""
        self._post(path='/api/v1/foo')
        resp = self._post(path='/api/v1/bar')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_different_auth_is_allowed(self):
        """Two users sending the same body to the same endpoint are independent."""
        self._post(auth='Bearer user1')
        resp = self._post(auth='Bearer user2')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_different_method_is_allowed(self):
        """PUT after POST to the same path is not a duplicate."""
        self._post()
        req = self.factory.put(
            '/',
            data='{"a":1}',
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer token123',
        )
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # Exempt methods                                                       #
    # ------------------------------------------------------------------ #

    def test_get_request_is_never_blocked(self):
        """GET is read-only; the middleware must never block it."""
        req1 = self.factory.get('/', HTTP_AUTHORIZATION='Bearer token123')
        req2 = self.factory.get('/', HTTP_AUTHORIZATION='Bearer token123')
        self.middleware(req1)
        resp = self.middleware(req2)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_multipart_post_is_exempt(self):
        """Multipart/file-upload requests must not be fingerprinted or blocked."""
        req1 = self.factory.post(
            '/',
            data={'file': b'data'},
            format='multipart',
            HTTP_AUTHORIZATION='Bearer token123',
        )
        req2 = self.factory.post(
            '/',
            data={'file': b'data'},
            format='multipart',
            HTTP_AUTHORIZATION='Bearer token123',
        )
        self.middleware(req1)
        resp = self.middleware(req2)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # Fallback identity (no auth header)                                  #
    # ------------------------------------------------------------------ #

    def test_uses_ip_when_no_auth_header(self):
        """Requests without Authorization header are fingerprinted by IP."""
        req1 = self.factory.post('/', data='{}', content_type='application/json',
                                 REMOTE_ADDR='1.2.3.4')
        req2 = self.factory.post('/', data='{}', content_type='application/json',
                                 REMOTE_ADDR='1.2.3.4')
        req3 = self.factory.post('/', data='{}', content_type='application/json',
                                 REMOTE_ADDR='9.9.9.9')
        self.middleware(req1)
        # Same IP → blocked
        resp_same = self.middleware(req2)
        self.assertEqual(resp_same.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Different IP → allowed
        resp_diff = self.middleware(req3)
        self.assertEqual(resp_diff.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # Window expiry                                                        #
    # ------------------------------------------------------------------ #

    def test_request_allowed_after_window_expires(self):
        """After the cache key expires the same request must be allowed again."""
        from unittest.mock import patch
        self._post()
        # Simulate cache expiry by deleting the key directly
        with patch('api.common.middleware.cache') as mock_cache:
            mock_cache.get.return_value = None  # key has expired
            mock_cache.set.return_value = None
            resp = self._post()
        # The patched cache sees no existing key, so the request goes through
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
