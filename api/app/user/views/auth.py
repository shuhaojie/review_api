from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed

from api.app.user.serializers.custom import CustomTokenObtainPairSerializer
from api.app.user.serializers.request import (RegisterRequestSerializer, LoginRequestSerializer,
                                              EmailVerificationRequestSerializer)
from api.app.user.serializers.response import LoginResponseSerializer
from api.common.http.response import BaseResponse
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.views import BaseAPIView
from api.common.utils.logger import logger
from api.common.utils.email import EmailVerification


class RegisterView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Register",
        operation_description="Register a new account after verifying the email confirmation code.",
        request_body=RegisterRequestSerializer,
        responses={
            201: openapi.Response(description="Registered successfully", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            verification_code = serializer.validated_data['verification_code']
            is_valid, message = EmailVerification.verify_code(email, verification_code)

            if not is_valid:
                return BaseResponse.error(message)
            serializer.save()
            return BaseResponse.created(message="Registered successfully")
        return BaseResponse.error(serializer.errors)


class VerifyCodeView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Send verification code",
        operation_description="Send a one-time verification code to the provided email address.",
        request_body=EmailVerificationRequestSerializer,
        responses={
            201: openapi.Response(description="Verification code sent", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return BaseResponse.error(serializer.errors)
        email = serializer.validated_data['email']
        try:
            verification_code = EmailVerification.generate_verification_code()
            logger.info(f"verification_code={verification_code}")
            success = EmailVerification.send_verification_email(email, verification_code)
            if success:
                logger.info(f"Verification code [{verification_code}] sent successfully.")
                EmailVerification.save_verification_code(email, verification_code)
                return BaseResponse.created(
                    message="Verification code sent"
                )
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
