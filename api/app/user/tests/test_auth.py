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

    # ---------- 正常流 ----------

    def test_register_success(self):
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='alice')
        self.assertEqual(user.email, 'alice@example.com')
        # 密码应被加密存储
        self.assertNotEqual(user.password, 'test1234')
        self.assertTrue(user.check_password('test1234'))

    # ---------- 验证码相关 ----------

    def test_register_invalid_verification_code(self):
        """验证码错误时应返回 400"""
        with self._mock_verify_code(False, '验证码错误或已过期'):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_register_missing_verification_code(self):
        """缺少 verification_code 时应返回 400"""
        payload = {**self.valid_payload}
        payload.pop('verification_code')
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verification_code', resp.data['message'])

    def test_register_verification_code_wrong_length(self):
        """verification_code 长度不为 6 时应返回 400"""
        payload = {**self.valid_payload, 'verification_code': '123'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verification_code', resp.data['message'])

    # ---------- 用户名校验 ----------

    def test_register_duplicate_username(self):
        """用户名已存在时应返回 400"""
        User.objects.create_user(username='alice', password='abc123')
        with self._mock_verify_code(True):
            resp = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_username_too_short(self):
        """用户名少于 3 个字符时应返回 400"""
        payload = {**self.valid_payload, 'username': 'ab'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])

    def test_register_username_too_long(self):
        """用户名超过 32 个字符时应返回 400"""
        payload = {**self.valid_payload, 'username': 'a' * 33}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])

    # ---------- 密码校验 ----------

    def test_register_weak_password(self):
        """密码少于 5 个字符时应返回 400"""
        payload = {**self.valid_payload, 'password': '123', 'password_confirm': '123'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data['message'])

    def test_register_different_password(self):
        """两次密码不一致时应返回 400"""
        payload = {**self.valid_payload, 'password_confirm': 'different'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- 邮箱校验 ----------

    def test_register_invalid_email(self):
        """邮箱格式非法时应返回 400"""
        payload = {**self.valid_payload, 'email': 'not-an-email'}
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])

    # ---------- 缺少必填字段 ----------

    def test_register_missing_all_fields(self):
        """完全空请求应返回 400，并报告必填字段"""
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data['message'])


class VerifyCodeTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('verify_code')

    # ---------- 正常流 ----------

    def test_verify_code_success(self):
        """有效邮箱应成功发送验证码"""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='654321'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=True), \
             patch('api.app.user.views.auth.EmailVerification.save_verification_code') as mock_save:
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_save.assert_called_once_with('new@example.com', '654321')

    # ---------- 异常流 ----------

    def test_verify_code_email_already_registered(self):
        """已注册邮箱应返回 400"""
        User.objects.create_user(username='existing', email='taken@example.com', password='pass1234')
        resp = self.client.post(self.url, {'email': 'taken@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_code_send_failure(self):
        """邮件发送失败时应返回 400"""
        with patch('api.app.user.views.auth.EmailVerification.generate_verification_code', return_value='123456'), \
             patch('api.app.user.views.auth.EmailVerification.send_verification_email', return_value=False):
            resp = self.client.post(self.url, {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_code_missing_email(self):
        """缺少 email 字段时应返回 400"""
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])

    def test_verify_code_invalid_email_format(self):
        """邮箱格式非法时应返回 400"""
        resp = self.client.post(self.url, {'email': 'not-valid'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.data['message'])
