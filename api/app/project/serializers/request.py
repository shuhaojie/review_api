from rest_framework import serializers
from api.app.project.models import Project
from api.app.base.serializers.request import BaseRequestValidationSerializer


class CreateProjectSerializer(BaseRequestValidationSerializer):
    name = serializers.CharField(max_length=32, error_messages={"max_length": "Length cannot exceed 32 characters"})
    viewers = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        user = self.context['request'].user
        if Project.objects.filter(name=attrs['name'], owner=user).exists():
            raise serializers.ValidationError('You have already created a project with the same name')
        return attrs

    def create(self, validated_data):
        viewers = validated_data.pop('viewers', [])  # What is passed in is [1,2,3]
        project = Project.objects.create(**validated_data)
        # 3. Then handle the many-to-many relationship (assuming viewers is a ManyToManyField pointing to User)
        if viewers:
            project.viewers.set(viewers)  # One-time association
        return project
