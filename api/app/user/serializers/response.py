# myapp/serializers.py
from rest_framework import serializers
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.user.models import User, Group


class RegisterResponseSerializer(BaseResponseSerializer):
    class RegisterDataSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        email = serializers.EmailField()
        access = serializers.CharField(help_text="JWT access token")
        refresh = serializers.CharField(help_text="JWT refresh token")

    data = RegisterDataSerializer()


class LoginResponseSerializer(BaseResponseSerializer):
    class LoginDataSerializer(serializers.Serializer):
        refresh = serializers.CharField()
        access = serializers.CharField()
        is_admin = serializers.BooleanField()

    data = LoginDataSerializer()


class UserMetaResponseSerializer(serializers.ModelSerializer):
    # Custom groups field, returns user group ID and name
    groups = serializers.SerializerMethodField()
    
    def get_groups(self, obj):
        # Return all user groups that the user belongs to with their ID and name
        return [{'id': group.id, 'name': group.name} for group in obj.groups.all()]
    
    class Meta:
        model = User
        exclude = ['password']


class UserListResponseSerializer(BaseResponseSerializer):
    data = UserMetaResponseSerializer(many=True)

    class Meta:
        pass


class UserDetailResponseSerializer(serializers.ModelSerializer):
    # Custom groups field, returns user group ID and name
    groups = serializers.SerializerMethodField()
    
    def get_groups(self, obj):
        # Return all user groups that the user belongs to with their ID and name
        return [{'id': group.id, 'name': group.name} for group in obj.groups.all()]
    
    class Meta:
        model = User
        exclude = ['password']


class GroupMetaResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class GroupListResponseSerializer(BaseResponseSerializer):
    data = GroupMetaResponseSerializer(many=True)

    class Meta:
        pass


class GroupDetailResponseSerializer(BaseResponseSerializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    users = serializers.SerializerMethodField()

    def get_users(self, obj):
        # Use the correct related_name 'user_groups' to get group members
        return UserListResponseSerializer(obj.user_groups.all(), many=True).data