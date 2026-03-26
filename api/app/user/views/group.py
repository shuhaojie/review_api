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
        operation_summary="List groups",
        operation_description="Return a paginated list of all user groups.",
        query_serializer=BaseGetRequestSerializer(),
        responses={
            200: openapi.Response(description="Success", schema=GroupListResponseSerializer(many=True)),
            401: openapi.Response(description="Unauthorized"),
        }
    )
    def get(self, request):
        groups = Group.objects.all()
        q = request.query_params.get('q')
        if q:
            groups = groups.filter(name__icontains=q)
        return PaginationHelper.paginate_queryset(groups, request, GroupMetaResponseSerializer)

    @swagger_auto_schema(
        operation_summary="Create group",
        operation_description="Create a new user group. Optionally add users at creation time.",
        request_body=GroupCreateRequestSerializer(),
        responses={
            201: openapi.Response(description="Created successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            400: openapi.Response(description="Validation error"),
        }
    )
    def post(self, request):
        serializer = GroupCreateRequestSerializer(data=request.data)
        if serializer.is_valid():
            group_name = serializer.validated_data['name']
            description = serializer.validated_data.get('description', '')
            if Group.objects.filter(name=group_name).exists():
                return BaseResponse.error("A group with that name already exists.")
            group = Group.objects.create(name=group_name, description=description)
            user_ids = serializer.validated_data.get('user_ids', [])
            if user_ids:
                users = User.objects.filter(id__in=user_ids)
                group.user_groups.set(users)
            return BaseResponse.created()
        return BaseResponse.error("Validation error", data=serializer.errors)


class GroupDetailView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get group detail",
        operation_description="Return detailed information for the specified group, including its members.",
        responses={
            200: openapi.Response(description="Success", schema=GroupDetailResponseSerializer()),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Group not found"),
        }
    )
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            serializer = GroupDetailResponseSerializer(group)
            return BaseResponse.success(data=serializer.data)
        except Group.DoesNotExist:
            return BaseResponse.error("Group not found.", code=404)

    @swagger_auto_schema(
        operation_summary="Update group",
        operation_description="Update the specified group's name, description, or member list.",
        request_body=GroupUpdateRequestSerializer(),
        responses={
            200: openapi.Response(description="Updated successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Group not found"),
        }
    )
    def put(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return BaseResponse.error("Group not found.", code=404)
        serializer = GroupUpdateRequestSerializer(data=request.data)
        if serializer.is_valid():
            if 'name' in serializer.validated_data:
                group.name = serializer.validated_data['name']
            if 'description' in serializer.validated_data:
                group.description = serializer.validated_data['description']
            if 'user_ids' in serializer.validated_data:
                user_ids = serializer.validated_data['user_ids']
                if user_ids:
                    users = User.objects.filter(id__in=user_ids)
                    group.user_groups.set(users)
                else:
                    group.user_groups.clear()
            group.save()
            return BaseResponse.modified()
        return BaseResponse.error("Validation error", data=serializer.errors)

    @swagger_auto_schema(
        operation_summary="Delete group",
        operation_description="Delete the specified user group.",
        responses={
            200: openapi.Response(description="Deleted successfully", schema=BaseResponseSerializer),
            401: openapi.Response(description="Unauthorized"),
            404: openapi.Response(description="Group not found"),
        }
    )
    def delete(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            group.delete()
            return BaseResponse.deleted()
        except Group.DoesNotExist:
            return BaseResponse.error("Group not found.", code=404)
