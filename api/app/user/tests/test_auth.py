from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from api.app.user.models import User


class RegisterTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('register')
        self.valid_payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'test1234',
            'password_confirm': 'test1234',
            'verification_code': '123456',
        }

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

    # ---------- Username validation ----------

    def test_register_duplicate_username(self):
        """Should return 400 when the username is already taken."""
        User.objects.create_user(username='alice', password='abc123')
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

    # ---------- Password validation ----------

    def test_register_weak_password(self):
        """Should return 400 when password is fewer than 5 characters."""
        payload = {**self.valid_payload, 'password': '123', 'password_confirm': '123'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data['message'])

    def test_register_different_password(self):
        """Should return 400 when passwords do not match."""
        payload = {**self.valid_payload, 'password_confirm': 'different'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- Email validation ----------

    def test_register_invalid_email(self):
        """Should return 400 when the email address is malformed."""
        payload = {**self.valid_payload, 'email': 'not-an-email'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])

    # ---------- Missing required fields ----------

    def test_register_missing_all_fields(self):
        """Should return 400 with required-field errors when the body is empty."""
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])


class VerifyCodeTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('verify_code')

    # ---------- Happy path ----------

    def test_verify_code_success(self):
        """Should send a verification code to a valid, unregistered email address."""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='654321'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=True), \
             patch('api.app.user.views.auth.EmailVerification.save_verification_code') as mock_save:
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_save.assert_called_once_with('new@example.com', '654321')

    # ---------- Error cases ----------

    def test_verify_code_email_already_registered(self):
        """Should return 400 when the email address is already registered."""
        User.objects.create_user(username='existing', email='taken@example.com', password='pass1234')
        resp = self.client.post(self.url, {'email': 'taken@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

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
