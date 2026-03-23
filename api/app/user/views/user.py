from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from api.app.user.serializers.request import UserCreateRequestSerializer, UserUpdateRequestSerializer
from api.app.user.serializers.response import (UserListResponseSerializer, UserMetaResponseSerializer,
                                               UserDetailResponseSerializer)
from api.app.user.models import User
from api.common.http.response import BaseResponse
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.views import BaseAPIView
from api.common.http.pagination import PaginationHelper


class UserListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List users",
        operation_description="Return a paginated list of all users.",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=UserListResponseSerializer(many=True)),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def get(self, request):
        q = request.GET.get('q', '')
        users = User.objects.filter(is_deleted=False).order_by('id')
        if q:
            users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
        return PaginationHelper.paginate_queryset(users, request, UserMetaResponseSerializer)


class UserCreateView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create user",
        operation_description="Create a new user account. Optionally assign the user to one or more groups.",
        request_body=UserCreateRequestSerializer(),
        responses={
            201: openapi.Response(description="Created successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            400: openapi.Response(description="Validation error"),
        }
    )
    def post(self, request):
        if not request.user.is_superuser:
            return BaseResponse.error("Only administrators can create users.", code=403)

        serializer = UserCreateRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return BaseResponse.created("User created successfully.")
        return BaseResponse.error("Validation error", data=serializer.errors)


class CurrentUserView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get user detail",
        operation_description="Return detailed information for the specified user, including id, username, email, and permissions.",
        responses={
            200: openapi.Response(description="Success", schema=UserDetailResponseSerializer()),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="User not found"),
        }
    )
    def get(self, request, user_id=None):
        try:
            if user_id:
                user = User.objects.get(id=user_id, is_deleted=False)
            else:
                user = request.user

            serializer = UserDetailResponseSerializer(user)
            return BaseResponse.success(data=serializer.data)
        except User.DoesNotExist:
            return BaseResponse.error("User not found.", code=404)


class UserDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update user",
        operation_description="Update the specified user's information. Supports updating username, email, password, and group membership.",
        request_body=UserUpdateRequestSerializer(),
        responses={
            200: openapi.Response(description="Updated successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            404: openapi.Response(description="User not found"),
            400: openapi.Response(description="Validation error"),
        }
    )
    def put(self, request, user_id):
        try:
            if not request.user.is_superuser:
                return BaseResponse.error("Only administrators can update user information.", code=403)

            user = User.objects.get(id=user_id, is_deleted=False)

            serializer = UserUpdateRequestSerializer(instance=user,
                                                     data=request.data,
                                                     context={'user_id': user_id})

            if serializer.is_valid():
                serializer.save()
                return BaseResponse.modified("User updated successfully.")

            return BaseResponse.error("Validation error", data=serializer.errors)
        except User.DoesNotExist:
            return BaseResponse.error("User not found.", code=404)

    @swagger_auto_schema(
        operation_summary="Delete user",
        operation_description="Soft-delete the specified user.",
        responses={
            200: openapi.Response(description="Deleted successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            404: openapi.Response(description="User not found"),
        }
    )
    def delete(self, request, user_id):
        try:
            if not request.user.is_superuser:
                return BaseResponse.error("Only administrators can delete users.", code=403)

            user = User.objects.get(id=user_id, is_deleted=False)

            if user.is_superuser and user.id != request.user.id:
                return BaseResponse.error("Cannot delete another superuser.", code=403)

            if user.id == request.user.id:
                return BaseResponse.error("Cannot delete your own account.", code=403)

            user.is_deleted = 1
            user.save()

            return BaseResponse.deleted("User deleted successfully.")
        except User.DoesNotExist:
            return BaseResponse.error("User not found.", code=404)
