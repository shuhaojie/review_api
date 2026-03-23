from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed

from api.app.user.models import User
from api.app.user.serializers.custom import CustomTokenObtainPairSerializer
from api.app.user.serializers.request import (RegisterRequestSerializer, LoginRequestSerializer,
                                              EmailVerificationRequestSerializer)
from api.app.user.serializers.response import LoginResponseSerializer, RegisterResponseSerializer
from api.common.http.response import BaseResponse
from api.app.base.views import BaseAPIView
from api.common.utils.logger import logger
from api.common.utils.email import EmailVerification

# Uniform message used for verify-code responses to prevent email enumeration
_VERIFY_CODE_SENT_MSG = "If this email address is not already registered, a verification code has been sent."


class RegisterView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Register",
        operation_description=(
            "Register a new account after verifying the email confirmation code. "
            "Requires the user to accept the terms of service (terms_accepted=true). "
            "On success, returns JWT access and refresh tokens so the client is immediately authenticated. "
            "Rate limited to 5 failed attempts per email per hour."
        ),
        request_body=RegisterRequestSerializer,
        responses={
            201: openapi.Response(description="Registered successfully", schema=RegisterResponseSerializer)
        }
    )
    def post(self, request):
        email = request.data.get('email', '')

        # Check registration rate limit before any processing
        allowed, rate_message = EmailVerification.check_register_rate_limit(email)
        if not allowed:
            return BaseResponse.error(rate_message)

        serializer = RegisterRequestSerializer(data=request.data)
        if not serializer.is_valid():
            EmailVerification.record_register_attempt(email)
            return BaseResponse.error(serializer.errors)

        verification_code = serializer.validated_data['verification_code']
        is_valid, message = EmailVerification.verify_code(email, verification_code)
        if not is_valid:
            EmailVerification.record_register_attempt(email)
            return BaseResponse.error(message)

        user = serializer.save()
        EmailVerification.clear_register_attempts(email)

        refresh = RefreshToken.for_user(user)
        return BaseResponse.created(
            data={
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            message="Registered successfully"
        )


class VerifyCodeView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Send verification code",
        operation_description=(
            "Send a one-time verification code to the provided email address. "
            "Rate limited to 1 request per 5 minutes and 3 requests per day per address."
        ),
        request_body=EmailVerificationRequestSerializer,
        responses={
            201: openapi.Response(description="Verification code sent", schema=RegisterResponseSerializer)
        }
    )
    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return BaseResponse.error(serializer.errors)

        email = serializer.validated_data['email']

        # Check rate limit before doing anything else
        allowed, rate_message = EmailVerification.check_send_rate_limit(email)
        if not allowed:
            return BaseResponse.error(rate_message)

        # If the email is already registered, return the same response as success
        # to avoid revealing which addresses are in the system (email enumeration protection)
        if User.objects.filter(email=email).exists():
            return BaseResponse.created(message=_VERIFY_CODE_SENT_MSG)

        try:
            verification_code = EmailVerification.generate_verification_code()
            logger.info(f"verification_code={verification_code}")
            success = EmailVerification.send_verification_email(email, verification_code)
            if success:
                logger.info(f"Verification code [{verification_code}] sent to {email}.")
                EmailVerification.save_verification_code(email, verification_code)
                EmailVerification.record_send(email)
                return BaseResponse.created(message=_VERIFY_CODE_SENT_MSG)
            else:
                logger.info(f"Failed to send verification code [{verification_code}].")
                return BaseResponse.error("Failed to send verification code. Please try again later.")
        except Exception as e:
            logger.error(f"Exception when sending verification code: {str(e)}")
            return BaseResponse.error("An unexpected error occurred. Please try again later.")


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_summary="Login",
        operation_description="Authenticate with username and password and receive JWT tokens.",
        request_body=LoginRequestSerializer,
        responses={
            200: openapi.Response(description="Login successful", schema=LoginResponseSerializer)
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            return BaseResponse.success(data=response.data, message="Login successful")
        except AuthenticationFailed as e:
            logger.exception(e)
            return BaseResponse.error(message="Invalid username or password.")
        except Exception as e:
            logger.exception(e)
            return BaseResponse.error(message="Login failed.")
