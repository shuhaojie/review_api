from unittest.mock import patch
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from api.app.user.models import User


_LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(CACHES=_LOCMEM_CACHE)
class RegisterTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('register')
        self.valid_payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'test1234',
            'password_confirm': 'test1234',
            'verification_code': '123456',
            'terms_accepted': True,
        }

    def tearDown(self):
        cache.clear()

    def _mock_verify_code(self, success=True, message='ok'):
        return patch(
            'api.app.user.views.auth.EmailVerification.verify_code',
            return_value=(success, message)
        )

    # ---------- Happy path ----------

    def test_register_success(self):
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='alice')
        self.assertEqual(user.email, 'alice@example.com')
        # Password must be stored as a hash, not plaintext
        self.assertNotEqual(user.password, 'test1234')
        self.assertTrue(user.check_password('test1234'))

    def test_register_success_returns_tokens_and_user_info(self):
        """Success response must include JWT tokens and basic user info."""
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data['data']
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIn('id', data)
        self.assertEqual(data['username'], 'alice')
        self.assertEqual(data['email'], 'alice@example.com')

    # ---------- Registration rate limiting ----------

    def test_register_blocked_after_max_failed_attempts(self):
        """Should return 400 once the per-email failed-attempt limit is reached."""
        from api.common.utils.email import MAX_REGISTER_ATTEMPTS
        cache.set(f'register_attempts_{self.valid_payload["email"]}', MAX_REGISTER_ATTEMPTS, 3600)
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_attempt_counter_cleared_on_success(self):
        """A successful registration must clear the failed-attempt counter."""
        from api.common.utils.email import MAX_REGISTER_ATTEMPTS
        cache.set(f'register_attempts_{self.valid_payload["email"]}', MAX_REGISTER_ATTEMPTS - 1, 3600)
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(cache.get(f'register_attempts_{self.valid_payload["email"]}'), None)

    # ---------- Verification code ----------

    def test_register_invalid_verification_code(self):
        """Should return 400 when the verification code is wrong."""
        with self._mock_verify_code(False, 'Invalid or expired verification code.'):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_register_missing_verification_code(self):
        """Should return 400 when verification_code is absent."""
        payload = {**self.valid_payload}
        payload.pop('verification_code')
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verification_code', resp.data['message'])

    def test_register_verification_code_wrong_length(self):
        """Should return 400 when verification_code is not 6 characters."""
        payload = {**self.valid_payload, 'verification_code': '123'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verification_code', resp.data['message'])

    # ---------- Terms of service ----------

    def test_register_terms_not_accepted(self):
        """Should return 400 when terms_accepted is False."""
        payload = {**self.valid_payload, 'terms_accepted': False}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_terms_missing(self):
        """Should return 400 when terms_accepted is absent."""
        payload = {**self.valid_payload}
        payload.pop('terms_accepted')
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Username validation ----------

    def test_register_duplicate_username(self):
        """Should return 400 when the username is already taken."""
        User.objects.create_user(username='alice', password='abc12345')
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_username_too_short(self):
        """Should return 400 when username is fewer than 3 characters."""
        payload = {**self.valid_payload, 'username': 'ab'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])

    def test_register_username_too_long(self):
        """Should return 400 when username exceeds 32 characters."""
        payload = {**self.valid_payload, 'username': 'a' * 33}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])

    def test_register_username_invalid_characters(self):
        """Should return 400 when username contains characters other than letters, digits, underscores, and hyphens."""
        for bad_username in ['ali ce', 'ali@ce', 'ali<script>', 'ali.ce']:
            with self.subTest(username=bad_username):
                payload = {**self.valid_payload, 'username': bad_username}
                resp = self.client.post(self.url, payload, format='json')
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Password validation ----------

    def test_register_password_too_short(self):
        """Should return 400 when password is fewer than 8 characters."""
        payload = {**self.valid_payload, 'password': 'abc123', 'password_confirm': 'abc123'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data['message'])

    def test_register_password_no_letters(self):
        """Should return 400 when password contains no letters."""
        payload = {**self.valid_payload, 'password': '12345678', 'password_confirm': '12345678'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data['message'])

    def test_register_password_no_digits(self):
        """Should return 400 when password contains no digits."""
        payload = {**self.valid_payload, 'password': 'abcdefgh', 'password_confirm': 'abcdefgh'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data['message'])

    def test_register_different_password(self):
        """Should return 400 when passwords do not match."""
        payload = {**self.valid_payload, 'password_confirm': 'different1'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Email validation ----------

    def test_register_invalid_email(self):
        """Should return 400 when the email address is malformed."""
        payload = {**self.valid_payload, 'email': 'not-an-email'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])

    def test_register_duplicate_email(self):
        """Should return 400 when the email address is already registered (TOCTOU guard)."""
        User.objects.create_user(username='bob', email='alice@example.com', password='pass1234')
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='alice').exists())

    # ---------- Missing required fields ----------

    def test_register_missing_all_fields(self):
        """Should return 400 with required-field errors when the body is empty."""
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])

    def test_register_missing_password_confirm(self):
        """Should return 400 when password_confirm is absent."""
        payload = {**self.valid_payload}
        payload.pop('password_confirm')
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Boundary values ----------

    def test_register_username_minimum_length(self):
        """Username with exactly 3 characters should be accepted."""
        payload = {**self.valid_payload, 'username': 'abc'}
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_register_password_minimum_length(self):
        """Password with exactly 8 characters containing a letter and a digit should be accepted."""
        payload = {**self.valid_payload, 'password': 'abcde123', 'password_confirm': 'abcde123'}
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    # ---------- Superuser promotion ----------

    def test_register_superuser_promotion(self):
        """Users whose username appears in SUPER_USER_LIST should be granted superuser status."""
        payload = {**self.valid_payload, 'username': 'admin'}
        with self._mock_verify_code(True), \
             patch('api.app.user.serializers.request.env.SUPER_USER_LIST', ['admin']):
            resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(username='admin').is_superuser)

    def test_register_normal_user_not_superuser(self):
        """Regular users should not be granted superuser status."""
        with self._mock_verify_code(True), \
             patch('api.app.user.serializers.request.env.SUPER_USER_LIST', []):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(User.objects.get(username='alice').is_superuser)

    # ---------- Response structure ----------

    def test_register_success_response_structure(self):
        """Success response must include success=True, code=201, and a message field."""
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['code'], status.HTTP_201_CREATED)
        self.assertIn('message', resp.data)

    def test_register_verification_code_not_stored_on_user(self):
        """verification_code must be stripped before the User record is saved."""
        with self._mock_verify_code(True):
            self.client.post(self.url, self.valid_payload, format='json')
        user = User.objects.get(username='alice')
        self.assertFalse(hasattr(user, 'verification_code'))


@override_settings(CACHES=_LOCMEM_CACHE)
class VerifyCodeTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('verify_code')

    def tearDown(self):
        cache.clear()

    # ---------- Happy path ----------

    def test_verify_code_success(self):
        """Should send a verification code to a valid, unregistered email address."""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='654321'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=True), \
             patch('api.app.user.views.auth.EmailVerification.save_verification_code') as mock_save, \
             patch('api.app.user.views.auth.EmailVerification.record_send'):
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_save.assert_called_once_with('new@example.com', '654321')

    # ---------- Email enumeration protection ----------

    def test_verify_code_email_already_registered_returns_201(self):
        """Should return 201 (not 400) when the email is already registered, to prevent enumeration."""
        User.objects.create_user(username='existing', email='taken@example.com', password='pass1234')
        resp = self.client.post(self.url, {'email': 'taken@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_verify_code_registered_email_does_not_send(self):
        """Should not actually send an email when the address is already registered."""
        User.objects.create_user(username='existing', email='taken@example.com', password='pass1234')
        with patch('api.app.user.views.auth.EmailVerification.send_verification_email') as mock_send:
            self.client.post(self.url, {'email': 'taken@example.com'}, format='json')
        mock_send.assert_not_called()

    # ---------- Rate limiting ----------

    def test_verify_code_5min_cooldown(self):
        """Should block a second identical request within 5 minutes (429 from idempotency middleware
        or 400 from view-level rate limiting — both indicate the request was rejected)."""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='123456'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=True), \
             patch('api.app.user.views.auth.EmailVerification.save_verification_code'), \
             patch('api.app.user.views.auth.EmailVerification.record_send',
                   side_effect=lambda email: cache.set(f'verify_cooldown_{email}', 1, 300)):
            self.client.post(self.url, {'email': 'new@example.com'}, format='json')
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_429_TOO_MANY_REQUESTS))

    def test_verify_code_daily_limit(self):
        """Should return 400 once the daily send limit (3) is reached."""
        cache.set('verify_daily_new@example.com', 3, 86400)
        resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Error cases ----------

    def test_verify_code_send_failure(self):
        """Should return 400 when the email fails to send."""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='123456'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=False):
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_code_missing_email(self):
        """Should return 400 when the email field is absent."""
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])

    def test_verify_code_invalid_email_format(self):
        """Should return 400 when the email address is malformed."""
        resp = self.client.post(self.url, {'email': 'not-valid'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])


@override_settings(CACHES=_LOCMEM_CACHE)
class VerifyCodeBruteForceTestCase(APITestCase):
    """
    Tests for brute-force protection on the verification code.
    These test EmailVerification.verify_code() directly (unit tests),
    since the brute-force logic lives in the utility class.
    """

    def setUp(self):
        from api.common.utils.email import EmailVerification
        self.ev = EmailVerification
        self.email = 'target@example.com'

    def tearDown(self):
        cache.clear()

    def _store_code(self, code='123456'):
        self.ev.save_verification_code(self.email, code)

    def test_correct_code_succeeds(self):
        """A correct code should return True."""
        self._store_code('123456')
        ok, _ = self.ev.verify_code(self.email, '123456')
        self.assertTrue(ok)

    def test_wrong_code_decrements_attempts(self):
        """A wrong code should return False and report remaining attempts."""
        self._store_code('999999')
        ok, msg = self.ev.verify_code(self.email, '000000')
        self.assertFalse(ok)
        self.assertIn('remaining', msg)

    def test_code_invalidated_after_max_attempts(self):
        """Code should be invalidated after MAX_VERIFY_ATTEMPTS consecutive failures."""
        from api.common.utils.email import MAX_VERIFY_ATTEMPTS
        self._store_code('999999')
        for _ in range(MAX_VERIFY_ATTEMPTS):
            self.ev.verify_code(self.email, '000000')
        # Even the correct code should now fail because the code was deleted
        ok, msg = self.ev.verify_code(self.email, '999999')
        self.assertFalse(ok)

    def test_attempt_counter_reset_on_new_code(self):
        """Saving a new code should reset the failed attempt counter."""
        from api.common.utils.email import MAX_VERIFY_ATTEMPTS
        self._store_code('999999')
        for _ in range(MAX_VERIFY_ATTEMPTS - 1):
            self.ev.verify_code(self.email, '000000')
        # Issue a new code — counter must reset
        self._store_code('111111')
        ok, _ = self.ev.verify_code(self.email, '111111')
        self.assertTrue(ok)

    def test_expired_code_returns_false(self):
        """An absent (expired) code should return False."""
        ok, msg = self.ev.verify_code(self.email, '123456')
        self.assertFalse(ok)
        self.assertIn('expired', msg.lower())
