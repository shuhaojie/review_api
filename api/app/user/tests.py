from django.urls import reverse
from rest_framework.test import APITestCase  # 如果不用 DRF 就换成 django.test.TestCase
from rest_framework import status
from api.app.user.models import User


class RegisterTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('register')  # 对应 urls 中的 name='register'

    # ---------- 正常流 ----------
    def test_register_success(self):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'test1234',
            'password_confirm': 'test1234',
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='alice').exists())
        # 密码应被加密
        user = User.objects.get(username='alice')
        self.assertNotEqual(user.password, 'test1234')
        self.assertTrue(user.check_password('test1234'))

    # ---------- 异常流 ----------
    def test_register_duplicate_username(self):
        User.objects.create_user(username='alice', password='abc123')
        payload = {
            'username': 'alice',
            'email': 'new@example.com',
            'password': 'test1234',
            'password_confirm': 'test1234',
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # self.assertIn('username', resp.data)

    def test_register_weak_password(self):
        payload = {
            'username': 'bob',
            'email': 'bob@example.com',
            'password': '123'  # 短密码
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data)

    def test_register_different_password(self):
        payload = {
            'username': 'bob',
            'email': 'bob@example.com',
            'password': 'test123',
            'password_confirm': 'test12345',
        }
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # self.assertIn('password', resp.data)

    # ---------- 边界 ----------
    def test_register_missing_field(self):
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resp.data)
        self.assertIn('password', resp.data)
