from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed
from api.app.user.serializers.custom import CustomTokenObtainPairSerializer
from api.app.user.serializers.request import (RegisterRequestSerializer, LoginRequestSerializer,
                                              EmailVerificationRequestSerializer, GroupCreateRequestSerializer,
                                              GroupUpdateRequestSerializer, UserCreateRequestSerializer,
                                              UserUpdateRequestSerializer)
from api.app.user.serializers.response import (GroupListResponseSerializer, GroupMetaResponseSerializer,
                                               LoginResponseSerializer, UserListResponseSerializer,
                                               UserMetaResponseSerializer, UserDetailResponseSerializer,
                                               GroupDetailResponseSerializer)
from api.app.user.models import User, Group
from api.app.base.http.response import BaseResponse
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.views import BaseAPIView
from api.common.utils.logger import logger
from api.common.utils.pagination import PaginationHelper
from api.common.utils.email_utils import EmailVerification
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q


class RegisterView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="User Registration",
        operation_description="User registration interface, creates account after verifying email verification code",
        request_body=RegisterRequestSerializer,
        responses={
            201: openapi.Response(description="Registration successful", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        # is_valid: Validates if parameters are legal, first validates fields, then validates [field_name_validator], and finally validates the validate method
        if serializer.is_valid():
            email = serializer.validated_data['email']
            verification_code = serializer.validated_data['verification_code']
            is_valid, message = EmailVerification.verify_code(email, verification_code)

            if not is_valid:
                return BaseResponse.error(message)
            serializer.save()
            return BaseResponse.created(message="Registration successful")
        return BaseResponse.error(serializer.errors)


class VerifyCodeView(BaseAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Get Verification Code",
        operation_description="Get verification code via email during registration",
        request_body=EmailVerificationRequestSerializer,
        responses={
            201: openapi.Response(description="Verification code sent successfully", schema=BaseResponseSerializer)
        }
    )
    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return BaseResponse.error(serializer.errors)
        email = serializer.validated_data['email']
        try:
            # Generate verification code
            verification_code = EmailVerification.generate_verification_code()
            logger.info(f"verification_code={verification_code}")
            # Send email
            success = EmailVerification.send_verification_email(email, verification_code)
            if success:
                logger.info(f"send verification code[{verification_code}] success")
                # Save verification code to cache
                EmailVerification.save_verification_code(email, verification_code)
                logger.info(f"save_verification_code={verification_code}")
                return BaseResponse.created(
                    message="Verification code sent successfully"
                )
            else:
                logger.info(f"send verification code[{verification_code}] failed.")
                return BaseResponse.error("Failed to send verification code, please try again later")
        except Exception as e:
            logger.error(f"Exception when sending verification code: {str(e)}")
            return BaseResponse.error("System exception, please try again later")


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_summary="User Login",
        operation_description="User login",
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
            # Username or password error
            return BaseResponse.error(message="Account or password error")
        except Exception as e:
            logger.exception(e)
            return BaseResponse.error(message="Login failed")


class UserListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User List",
        operation_description="Get list of all users in the system, including id and username information",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=UserListResponseSerializer(many=True)),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def get(self, request):
        # Get search parameters
        q = request.GET.get('q', '')
        # Build query set
        users = User.objects.filter(is_deleted=False).order_by('id')
        # If there are search keywords, filter results
        if q:
            users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
        return PaginationHelper.paginate_queryset(users, request, UserMetaResponseSerializer)


class UserCreateView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create User",
        operation_description="Admin creates new user, supports selecting user groups",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        request_body=UserCreateRequestSerializer(),
        responses={
            201: openapi.Response(description="Creation successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            400: openapi.Response(description="Request parameter error"),
        }
    )
    def post(self, request):
        # Check if current user is admin
        if not request.user.is_superuser:
            return BaseResponse.error("Only admin can create users", code=403)

        serializer = UserCreateRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return BaseResponse.created("User created successfully")
        return BaseResponse.error("Request parameter error", data=serializer.errors)


class CurrentUserView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User Detail",
        operation_description="Get detailed information of specified user based on user ID, including id, username, email, permissions, etc.",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(description="Get successful", schema=UserDetailResponseSerializer()),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User does not exist"),
        }
    )
    def get(self, request, user_id=None):
        """Get user detailed information"""
        try:
            # If user_id is provided, get specified user
            if user_id:
                user = User.objects.get(id=user_id, is_deleted=False)
            else:
                # Otherwise get current logged-in user
                user = request.user

            serializer = UserDetailResponseSerializer(user)
            return BaseResponse.success(data=serializer.data, message="Get user detailed information successfully")
        except User.DoesNotExist:
            return BaseResponse.error("User does not exist", code=404)


class UserDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update User Information",
        operation_description="Update information of specified user based on user ID, supports updating username, email, password, user groups, etc.",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        request_body=UserUpdateRequestSerializer(),
        responses={
            200: openapi.Response(description="Update successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="No permission"),
            404: openapi.Response(description="User does not exist"),
            400: openapi.Response(description="Request parameter error"),
        }
    )
    def put(self, request, user_id):
        try:
            # Check if current user is admin
            if not request.user.is_superuser:
                return BaseResponse.error("Only admin can update user information", code=403)

            # Get user to update
            user = User.objects.get(id=user_id, is_deleted=False)

            # Create serializer and pass user ID as context
            serializer = UserUpdateRequestSerializer(instance=user,
                                                     data=request.data,
                                                     context={'user_id': user_id})

            if serializer.is_valid():
                serializer.save()
                return BaseResponse.modified("User information updated successfully")

            return BaseResponse.error("Request parameter error", data=serializer.errors)
        except User.DoesNotExist:
            return BaseResponse.error("User does not exist", code=404)

    @swagger_auto_schema(
        operation_summary="Delete User",
        operation_description="Delete specified user based on user ID",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        responses={
            200: openapi.Response(description="Delete successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="No permission"),
            404: openapi.Response(description="User does not exist"),
        }
    )
    def delete(self, request, user_id):
        try:
            # Check if current user is admin
            if not request.user.is_superuser:
                return BaseResponse.error("Only admin can delete users", code=403)

            # Get user to delete
            user = User.objects.get(id=user_id, is_deleted=False)

            # Prevent deleting super admin
            if user.is_superuser and user.id != request.user.id:
                return BaseResponse.error("Cannot delete other super admins", code=403)

            # Prevent user from deleting themselves
            if user.id == request.user.id:
                return BaseResponse.error("Cannot delete your own account", code=403)

            # Execute delete operation
            user.is_deleted = 1
            user.save()

            return BaseResponse.deleted("User deleted successfully")
        except User.DoesNotExist:
            return BaseResponse.error("User does not exist", code=404)


class GroupListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User Group List",
        operation_description="Get list of all user groups in the system",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Get successful", schema=GroupListResponseSerializer(many=True)),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def get(self, request):
        # Get user group list
        groups = Group.objects.all()
        # Apply query parameters
        q = request.query_params.get('q')
        if q:
            groups = groups.filter(name__icontains=q)
        return PaginationHelper.paginate_queryset(groups, request, GroupMetaResponseSerializer)


class GroupDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User Group Detail",
        operation_description="Get detailed information of user group based on user group ID, including group members",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        responses={
            200: openapi.Response(description="Get successful", schema=GroupDetailResponseSerializer()),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User group does not exist"),
        }
    )
    def get(self, request, group_id):
        try:
            # Get user group
            group = Group.objects.get(id=group_id)
            # Serialize user group details
            serializer = GroupDetailResponseSerializer(group)
            return BaseResponse.success(data=serializer.data, message="Get user group details successfully")
        except Group.DoesNotExist:
            return BaseResponse.error("User group does not exist", code=404)

    @swagger_auto_schema(
        operation_summary="Update User Group",
        operation_description="Update information of specified user group based on user group ID, supports updating group members",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        request_body=GroupUpdateRequestSerializer(),
        responses={
            200: openapi.Response(description="Update successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User group does not exist"),
        }
    )
    def put(self, request, group_id):
        group = Group.objects.get(id=group_id)
        serializer = GroupUpdateRequestSerializer(data=request.data)
        if serializer.is_valid():
            # Update user group name
            if 'name' in serializer.validated_data:
                group.name = serializer.validated_data['name']
            if 'description' in serializer.validated_data:
                group.description = serializer.validated_data['description']
            # If user ID list is provided, update group members
            if 'user_ids' in serializer.validated_data:
                user_ids = serializer.validated_data['user_ids']
                if user_ids:
                    # Get existing users
                    users = User.objects.filter(id__in=user_ids)
                    # Update group members
                    group.user_groups.set(users)
                else:
                    # If user_ids is empty list, clear group members
                    group.user_groups.clear()
            # Save user group
            group.save()
            return BaseResponse.modified()
        return BaseResponse.error("Request parameter error", data=serializer.errors)

    @swagger_auto_schema(
        operation_summary="Delete User Group",
        operation_description="Delete specified user group based on user group ID",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        responses={
            201: openapi.Response(description="Delete successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User group does not exist"),
        }
    )
    def delete(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            group.delete()
            return BaseResponse.deleted()
        except Group.DoesNotExist:
            return BaseResponse.error("User group does not exist", code=404)


class GroupCreateView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create User Group",
        operation_description="Create new user group, supports adding users at the same time",
        manual_parameters=[
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description="JWT Token (obtained via /user/login endpoint), format: Bearer {token}",
                required=True,
            )
        ],
        request_body=GroupCreateRequestSerializer(),
        responses={
            201: openapi.Response(description="Creation successful", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            400: openapi.Response(description="Request parameter error"),
        }
    )
    def post(self, request):
        serializer = GroupCreateRequestSerializer(data=request.data)
        if serializer.is_valid():
            # Check if user group with the same name already exists
            group_name = serializer.validated_data['name']
            description = serializer.validated_data.get('description', '')
            if Group.objects.filter(name=group_name).exists():
                return BaseResponse.error("User group name already exists")
            # Create user group
            group = Group.objects.create(name=group_name, description=description)   
            # If user ID list is provided, add users to user group
            user_ids = serializer.validated_data.get('user_ids', [])
            if user_ids:
                # Get existing users
                users = User.objects.filter(id__in=user_ids)
                # Add users to user group
                group.user_groups.set(users)
            return BaseResponse.created()
        return BaseResponse.error("Request parameter error", data=serializer.errors)