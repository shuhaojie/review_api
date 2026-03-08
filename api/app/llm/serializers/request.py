from rest_framework import serializers
from api.app.llm.models import Prompt, LLMTest, TestSample, LLMProvider
from api.app.base.serializers.request import BaseRequestValidationSerializer


class CreatePromptRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=100)
    content = serializers.CharField(max_length=5000)

    class Meta:
        model = Prompt
        fields = ['name', 'content']

    def validate_name(self, value):
        # Idempotent: exclude self when updating
        view = self.context.get('view')
        if view and view.kwargs.get('pk'):  # PUT/PATCH
            if Prompt.objects.filter(name=value, is_deleted=0).exclude(pk=view.kwargs['pk']).exists():
                raise serializers.ValidationError("Name already exists, please change it")
        else:  # POST
            if Prompt.objects.filter(name=value, is_deleted=0).exists():
                raise serializers.ValidationError("Name already exists, please change it")
        return value


class UpdatePromptRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=100, required=False)
    content = serializers.CharField(max_length=5000, required=False,
                                    error_messages={"max_length": "Length cannot exceed 5000 characters"})
    is_active = serializers.BooleanField(
        required=True,  # Frontend can omit
        label='Is active',
        error_messages={
            'invalid': 'Is active must be true/false',
        }
    )

    class Meta:
        model = Prompt
        fields = ["is_active", "name", "content"]
        # id、is_active、creator are read-only
        read_only_fields = ['id', 'creator']


class CreateLLMProviderRequestSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=100)
    temperature = serializers.DecimalField(
        max_digits=4, decimal_places=2,
        min_value=0, max_value=2,
        help_text="Sampling temperature, 0~2, higher values are more random"
    )
    frequency_penalty = serializers.DecimalField(
        max_digits=4, decimal_places=2,
        min_value=-2, max_value=2,
        help_text="Repeat token penalty coefficient, -2~2"
    )
    top_p = serializers.DecimalField(
        max_digits=3, decimal_places=2,
        min_value=0, max_value=1,
        help_text="Top-P cumulative probability, 0~1"
    )
    chunk_length = serializers.IntegerField(
        min_value=1,
        max_value=32000,
        help_text="Maximum token count for single generation"
    )

    class Meta:
        model = LLMProvider
        fields = ["id", "name", "is_active", "temperature", "frequency_penalty", "top_p", "chunk_length", "description"]
class UpdateLLMProviderRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = [
            'name', 'description', 'is_active'
        ]
        # Note: Do not include read-only fields like id, create_time

class CreateTestSampleRequestSerializer(BaseRequestValidationSerializer):
    class Meta:
        model = TestSample
        fields = ['input', 'gold']


class UpdateTestSampleRequestSerializer(BaseRequestValidationSerializer):
    class Meta:
        model = TestSample
        fields = ['input', 'gold']


class CreateLLMTestRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMTest
        fields = ['prompt', 'provider', 'temperature', 'frequency_penalty',
                  'top_p', 'chunk_length']

    def create(self, validated_data):
        request = self.context.get('request')

        prompt = validated_data['prompt']

        # 🔥 Inject "snapshot logic" here
        validated_data['prompt_content_snapshot'] = prompt.content
        validated_data['creator'] = request.user

        return super().create(validated_data)
