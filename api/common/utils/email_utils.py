# utils/email_utils.py
import random
import logging
from django.core.mail import send_mail
from django.core.cache import cache
from api.settings.config import env

logger = logging.getLogger(__name__)


class EmailVerification:
    """Email verification utility class"""

    @staticmethod
    def generate_verification_code():
        """Generate 6-digit verification code"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    @staticmethod
    def send_verification_email(email, verification_code):
        """Send verification email"""
        try:
            subject = 'Your Registration Verification Code'
            message = f'''
            Thank you for registering our service!

            Your verification code is: {verification_code}

            The verification code is valid for 5 minutes, please complete the registration as soon as possible.

            If this is not your operation, please ignore this email.
            '''

            send_mail(
                subject=subject,
                message=message,
                from_email=env.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            logger.info(f"Verification email sent to: {email}")
            return True

        except Exception as e:
            logger.exception(f"Failed to send verification email: {str(e)}")
            return False

    @staticmethod
    def save_verification_code(email, verification_code):
        """Save verification code to cache"""
        cache_key = f'verification_code_{email}'
        cache.set(cache_key, verification_code, env.VERIFICATION_CODE_EXPIRE)

    @staticmethod
    def verify_code(email, code):
        """Verify verification code"""
        cache_key = f'verification_code_{email}'
        stored_code = cache.get(cache_key)

        if not stored_code:
            return False, "Verification code has expired, please get a new one"

        if stored_code != code:
            return False, "Invalid verification code"

        # Delete verification code after successful verification
        cache.delete(cache_key)
        return True, "Verification successful"
