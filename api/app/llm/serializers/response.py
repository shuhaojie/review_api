from rest_framework import serializers
from api.app.llm.models import Prompt, LLMTest, TestSample, LLMProvider
from api.app.user.models import User


class PromptListResponseSerializer(serializers.ModelSerializer):
    # 对create_time字段进行调整
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Prompt
        fields = ["id", "name", "content", "create_time", "creator_id", "creator_name", "is_active"]
        # ★ 新增

    creator_name = serializers.SerializerMethodField(read_only=True)

    def get_creator_name(self, obj):
        # obj.creator_id 就是用户主键，反向查 User 表
        if obj.creator_id is None:
            return ""
        try:
            return User.objects.get(pk=obj.creator_id).username
        except User.DoesNotExist:
            return ""


class LLMProviderResponseSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = LLMProvider
        fields = ["id", "name", "is_active",  "description",
                  "create_time", "creator_id", "creator_name"]

    creator_name = serializers.SerializerMethodField(read_only=True)

    def get_creator_name(self, obj):
        # obj.creator_id 就是用户主键，反向查 User 表
        if obj.creator_id is None:
            return ""

        # 方式2：不改动视图，直接跨表一条 SQL（简单直观）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=obj.creator_id).username
        except User.DoesNotExist:
            return ""


# 读出（带名称）
class LLMTestReadResponseSerializer(serializers.ModelSerializer):
    prompt_name = serializers.CharField(source='prompt.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = LLMTest
        fields = '__all__'

    creator_name = serializers.SerializerMethodField(read_only=True)

    def get_creator_name(self, obj):
        # obj.creator_id 就是用户主键，反向查 User 表
        if obj.creator_id is None:
            return ""

        # 方式2：不改动视图，直接跨表一条 SQL（简单直观）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=obj.creator_id).username
        except User.DoesNotExist:
            return ""


class TestSampleResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSample
        fields = ['id', 'input', 'gold', 'uid', "create_time", "creator_id", "creator_name"]

    creator_name = serializers.SerializerMethodField(read_only=True)

    def get_creator_name(self, obj):
        # obj.creator_id 就是用户主键，反向查 User 表
        if obj.creator_id is None:
            return ""
        # 方式2：不改动视图，直接跨表一条 SQL（简单直观）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=obj.creator_id).username
        except User.DoesNotExist:
            return ""


class TestSampleDetailResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSample
        fields = ['id', 'input', 'gold', 'uid', "create_time", "creator_id", "creator_name"]

    creator_name = serializers.SerializerMethodField(read_only=True)

    def get_creator_name(self, obj):
        # obj.creator_id 就是用户主键，反向查 User 表
        if obj.creator_id is None:
            return ""
        # 方式2：不改动视图，直接跨表一条 SQL（简单直观）
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=obj.creator_id).username
        except User.DoesNotExist:
            return ""


class CreateTestSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSample
        fields = ['input', 'gold']


class UpdateTestSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSample
        fields = ['input', 'gold']
