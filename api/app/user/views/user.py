from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from api.app.user.serializers.request import UserCreateRequestSerializer, UserUpdateRequestSerializer
from api.app.user.serializers.response import (UserListResponseSerializer, UserMetaResponseSerializer,
                                               UserDetailResponseSerializer)
from api.app.user.models import User
from api.app.base.http.response import BaseResponse
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.views import BaseAPIView
from api.common.utils.pagination import PaginationHelper


class UserListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User List",
        operation_description="Get list of all users in the system, including id and username information",
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
