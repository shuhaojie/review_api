from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated

from api.app.user.serializers.request import GroupCreateRequestSerializer, GroupUpdateRequestSerializer
from api.app.user.serializers.response import (GroupListResponseSerializer, GroupMetaResponseSerializer,
                                               GroupDetailResponseSerializer)
from api.app.user.models import User, Group
from api.common.http.response import BaseResponse
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.base.serializers.request import BaseGetRequestSerializer
from api.app.base.views import BaseAPIView
from api.common.http.pagination import PaginationHelper


class GroupListView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get User Group List",
        operation_description="Get list of all user groups in the system",
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
