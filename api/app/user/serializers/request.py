from rest_framework import serializers
from api.settings.config import env
from api.app.base.serializers.request import BaseRequestValidationSerializer
from api.app.user.models import User, Group


class RegisterRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.RegexField(
        r'^[a-zA-Z0-9_-]+$',
        min_length=3,
        max_length=32,
        error_messages={'invalid': 'Username may only contain letters, numbers, underscores, and hyphens.'}
    )
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    verification_code = serializers.CharField(max_length=6, min_length=6)
    terms_accepted = serializers.BooleanField()

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms of service to register.")
        return value

    def validate_password(self, value):
        if not any(c.isalpha() for c in value):
            raise serializers.ValidationError("Password must contain at least one letter.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError('Passwords do not match.')
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('That username is already taken.')
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError('That email address is already registered.')
        return attrs

    def create(self, validated_data):
        validated_data.pop('verification_code')
        validated_data.pop('terms_accepted')
        if validated_data["username"] in env.SUPER_USER_LIST:
            validated_data['is_superuser'] = 1
        validated_data["is_deleted"] = 0
        user = User.objects.create_user(**validated_data)
        return user


class LoginRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(help_text="Username", required=True)
    password = serializers.CharField(help_text="Password", required=True)


class EmailVerificationRequestSerializer(BaseRequestValidationSerializer):
    """Email verification code request serializer."""
    email = serializers.EmailField(required=True)


class GroupCreateRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=150, required=True, help_text="Group name")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="IDs of users to add to this group on creation"
    )
    description = serializers.CharField(required=False, help_text="Group description")


class GroupUpdateRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=150, required=True, help_text="Group name")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="IDs of users to assign to this group"
    )
    description = serializers.CharField(required=False, help_text="Group description")


class UserCreateRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(min_length=3, max_length=32, help_text="Username")
    email = serializers.EmailField(help_text="Email address")
    password = serializers.CharField(min_length=5, write_only=True, help_text="Password")
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="IDs of groups to assign to this user on creation"
    )

    def validate(self, attrs):
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('That username is already taken.')
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError('That email address is already registered.')
        return attrs

    def create(self, validated_data):
        group_ids = validated_data.pop('group_ids', [])
        user = User.objects.create_user(**validated_data)
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)
        return user


class UserUpdateRequestSerializer(BaseRequestValidationSerializer):
    username = serializers.CharField(min_length=3, max_length=32, required=False, help_text="Username")
    email = serializers.EmailField(required=False, help_text="Email address")
    password = serializers.CharField(min_length=5, write_only=True, required=False, help_text="Password")
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="IDs of groups to assign to this user"
    )
    is_superuser = serializers.BooleanField(required=False, help_text="Grant superuser (admin) privileges")

    def validate(self, attrs):
        if 'username' in attrs:
            if User.objects.filter(username=attrs['username']).exclude(id=self.context.get('user_id')).exists():
                raise serializers.ValidationError('That username is already taken.')

        if 'email' in attrs:
            if User.objects.filter(email=attrs['email']).exclude(id=self.context.get('user_id')).exists():
                raise serializers.ValidationError('That email address is already registered.')

        return attrs

    def update(self, instance, validated_data):
        if 'username' in validated_data:
            instance.username = validated_data['username']

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        if 'is_superuser' in validated_data:
            instance.is_superuser = validated_data['is_superuser']

        if 'group_ids' in validated_data:
            group_ids = validated_data['group_ids']
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                instance.groups.set(groups)
            else:
                instance.groups.clear()

        instance.save()
        return instance
