from rest_framework import serializers
from api.app.project.models import Project
from api.app.base.serializers.request import BaseRequestValidationSerializer


class CreateProjectSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=32, error_messages={"max_length": "Project name must be at most 32 characters."})
    viewers = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        user = self.context['request'].user
        if Project.objects.filter(name=attrs['name'], owner=user).exists():
            raise serializers.ValidationError('You already have a project with that name.')
        return attrs

    def create(self, validated_data):
        viewers = validated_data.pop('viewers', [])
        project = Project.objects.create(**validated_data)
        if viewers:
            project.viewers.set(viewers)
        return project
