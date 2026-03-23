import secrets
import logging
from django.core.mail import send_mail
from django.core.cache import cache
from api.settings.config import env

logger = logging.getLogger(__name__)

MAX_VERIFY_ATTEMPTS = 5    # Invalidate code after this many consecutive wrong attempts
MAX_SENDS_PER_DAY = 3      # Maximum verification emails per address per day
MIN_SEND_INTERVAL = 300    # Minimum seconds between sends (5 minutes)
MAX_REGISTER_ATTEMPTS = 5  # Maximum registration attempts per email per hour


class EmailVerification:
    """Email verification utility."""

    @staticmethod
    def generate_verification_code():
        """Generate a cryptographically secure 6-digit code."""
        return f'{secrets.randbelow(1_000_000):06d}'

    @staticmethod
    def send_verification_email(email, verification_code):
        """Send the verification code to the given email address."""
        try:
            subject = 'Your Registration Verification Code'
            message = (
                f'Thank you for registering!\n\n'
                f'Your verification code is: {verification_code}\n\n'
                f'The code is valid for {env.VERIFICATION_CODE_EXPIRE // 60} minutes. '
                f'If you did not request this, please ignore this email.'
            )
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

    # ------------------------------------------------------------------ #
    # Verify-code rate limiting                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def check_send_rate_limit(email):
        """
        Check whether sending a code to this address is permitted.
        Returns (allowed: bool, message: str).
        """
        if cache.get(f'verify_cooldown_{email}'):
            return False, "Please wait at least 5 minutes before requesting another code."

        daily_count = cache.get(f'verify_daily_{email}', 0)
        if daily_count >= MAX_SENDS_PER_DAY:
            return False, "You have reached the daily limit for verification code requests. Please try again tomorrow."

        return True, ""

    @staticmethod
    def record_send(email):
        """Record a successful send for rate-limiting purposes."""
        cache.set(f'verify_cooldown_{email}', 1, MIN_SEND_INTERVAL)
        daily_key = f'verify_daily_{email}'
        cache.set(daily_key, cache.get(daily_key, 0) + 1, 86400)

    # ------------------------------------------------------------------ #
    # Verification code storage and validation                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def save_verification_code(email, code):
        """Persist the verification code and reset the failure counter."""
        cache.set(f'verification_code_{email}', code, env.VERIFICATION_CODE_EXPIRE)
        cache.delete(f'verify_attempts_{email}')

    @staticmethod
    def verify_code(email, code):
        """
        Verify the submitted code against the stored one.
        Returns (valid: bool, message: str).
        Invalidates the code after MAX_VERIFY_ATTEMPTS consecutive failures.
        """
        code_key = f'verification_code_{email}'
        attempts_key = f'verify_attempts_{email}'

        stored_code = cache.get(code_key)
        if not stored_code:
            return False, "Verification code has expired. Please request a new one."

        attempts = cache.get(attempts_key, 0)
        if attempts >= MAX_VERIFY_ATTEMPTS:
            cache.delete(code_key)
            return False, "Too many failed attempts. Please request a new verification code."

        if stored_code != code:
            new_attempts = attempts + 1
            cache.set(attempts_key, new_attempts, env.VERIFICATION_CODE_EXPIRE)
            remaining = MAX_VERIFY_ATTEMPTS - new_attempts
            if remaining <= 0:
                cache.delete(code_key)
                return False, "Too many failed attempts. Please request a new verification code."
            return False, f"Invalid verification code. {remaining} attempt(s) remaining."

        cache.delete(code_key)
        cache.delete(attempts_key)
        return True, "Verification successful"

    # ------------------------------------------------------------------ #
    # Registration rate limiting                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def check_register_rate_limit(email):
        """
        Check whether a registration attempt for this email is permitted.
        Returns (allowed: bool, message: str).
        Limits to MAX_REGISTER_ATTEMPTS failed attempts per hour.
        """
        attempts = cache.get(f'register_attempts_{email}', 0)
        if attempts >= MAX_REGISTER_ATTEMPTS:
            return False, "Too many registration attempts for this email. Please try again later."
        return True, ""

    @staticmethod
    def record_register_attempt(email):
        """Record a failed registration attempt (resets after 1 hour)."""
        key = f'register_attempts_{email}'
        cache.set(key, cache.get(key, 0) + 1, 3600)

    @staticmethod
    def clear_register_attempts(email):
        """Clear the registration attempt counter after a successful registration."""
        cache.delete(f'register_attempts_{email}')
