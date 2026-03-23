# utils/token_utils.py
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth.models import User


class TokenDecoder:
    """Token decoding utility class"""

    @staticmethod
    def decode_access_token(token_string):
        """Decode Access Token"""
        try:
            token = AccessToken(token_string)
            return {
                'success': True,
                'payload': token.payload,
                'token': token
            }
        except TokenError as e:
            return {
                'success': False,
                'error': str(e),
                'payload': None
            }

    @staticmethod
    def decode_refresh_token(token_string):
        """Decode Refresh Token"""
        try:
            token = RefreshToken(token_string)
            return {
                'success': True,
                'payload': token.payload,
                'token': token
            }
        except TokenError as e:
            return {
                'success': False,
                'error': str(e),
                'payload': None
            }

    @staticmethod
    def get_user_from_token(token_string):
        """Get user object from Token"""
        result = TokenDecoder.decode_access_token(token_string)
        if not result['success']:
            return None

        user_id = result['payload'].get('user_id')
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return None
        return None

    @staticmethod
    def get_token_info(token_string):
        """Get detailed information of Token"""
        result = TokenDecoder.decode_access_token(token_string)
        if not result['success']:
            return result

        payload = result['payload']
        token_info = {
            'user_id': payload.get('user_id'),
            'username': payload.get('username'),
            'email': payload.get('email'),
            'issued_at': payload.get('iat'),  # Issuance time
            'expires_at': payload.get('exp'),  # Expiration time
            'token_type': payload.get('token_type', 'access'),
            'jti': payload.get('jti'),  # JWT ID
        }

        # Calculate remaining validity period (seconds)
        from time import time
        if token_info['expires_at']:
            token_info['expires_in'] = token_info['expires_at'] - int(time())

        result['token_info'] = token_info
        return result


token_decoder = TokenDecoder()


from rest_framework_simplejwt.authentication import JWTAuthentication


class FlexibleJWTAuthentication(JWTAuthentication):
    """Accepts raw tokens without the 'Bearer' prefix."""

    def get_raw_token(self, header):
        parts = header.split()
        if len(parts) == 1:
            return parts[0]
        return super().get_raw_token(header)
