# myapp/serializers.py
from rest_framework import serializers
from env import env
from api.app.base.serializers.request import BaseRequestValidationSerializer
from api.app.user.models import User, Group


class RegisterRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(min_length=3, max_length=32)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=5, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    verification_code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError('Two passwords do not match')
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('Username already exists')
        return attrs

    def create(self, validated_data):
        validated_data.pop('verification_code')
        if validated_data["username"] in env.SUPER_USER_LIST:
            validated_data['is_superuser'] = 1
        validated_data["is_deleted"] = 0
        user = User.objects.create_user(**validated_data)
        return user


class LoginRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(help_text="Username", required=True)
    password = serializers.CharField(help_text="Password", required=True)


class EmailVerificationRequestSerializer(BaseRequestValidationSerializer):
    """Email verification serializer"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Verify if email has been registered"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email has been registered")
        return value


class GroupCreateRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=150, required=True, help_text="User group name")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="User ID list, used to add specified users to the user group when creating the user group"
    )
    description = serializers.CharField(required=False, help_text="User group description")


class GroupUpdateRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=150, required=True, help_text="User group name")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="User ID list, used to update users in the user group"
    )
    description = serializers.CharField(required=False, help_text="User group description")


class UserCreateRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(min_length=3, max_length=32, help_text="Username")
    email = serializers.EmailField(help_text="Email")
    password = serializers.CharField(min_length=5, write_only=True, help_text="Password")
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="User group ID list, used to add the user to specified user groups when creating the user"
    )
    
    def validate(self, attrs):
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('Username already exists')
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError('Email has been registered')
        return attrs
    
    def create(self, validated_data):
        # Get and remove group_ids
        group_ids = validated_data.pop('group_ids', [])
        # Create user
        user = User.objects.create_user(**validated_data)
        # If group_ids is provided, add the user to specified user groups
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)
        return user


class UserUpdateRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(min_length=3, max_length=32, required=False, help_text="Username")
    email = serializers.EmailField(required=False, help_text="Email")
    password = serializers.CharField(min_length=5, write_only=True, required=False, help_text="Password")
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="User group ID list, used to update the user groups the user belongs to"
    )
    is_superuser = serializers.BooleanField(required=False, help_text="Whether it is a superuser")
    
    def validate(self, attrs):
        # Verify if username already exists (if a new username is provided)
        if 'username' in attrs:
            # Exclude the current user himself
            if User.objects.filter(username=attrs['username']).exclude(id=self.context.get('user_id')).exists():
                raise serializers.ValidationError('Username already exists')
        
        # Verify if email has been registered (if a new email is provided)
        if 'email' in attrs:
            # Exclude the current user himself
            if User.objects.filter(email=attrs['email']).exclude(id=self.context.get('user_id')).exists():
                raise serializers.ValidationError('Email has been registered')
        
        return attrs
    
    def update(self, instance, validated_data):
        # Update user basic information
        if 'username' in validated_data:
            instance.username = validated_data['username']
        
        if 'email' in validated_data:
            instance.email = validated_data['email']
        
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        
        if 'is_superuser' in validated_data:
            instance.is_superuser = validated_data['is_superuser']
        
        # Update user groups
        if 'group_ids' in validated_data:
            group_ids = validated_data['group_ids']
            if group_ids:
                # Get existing user groups
                groups = Group.objects.filter(id__in=group_ids)
                # Update the user groups the user belongs to
                instance.groups.set(groups)
            else:
                # If group_ids is an empty list, clear the user groups the user belongs to
                instance.groups.clear()
        
        # Save the updated user information
        instance.save()
        return instance
