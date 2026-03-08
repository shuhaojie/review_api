from rest_framework import serializers
from api.app.project.models import Project
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.user.models import User


class UserInfoSerializer(serializers.ModelSerializer):
    """Return desensitized fields, add or remove as needed"""

    class Meta:
        model = User
        fields = ('id', 'username')


class ProjectListResponseSerializer(BaseResponseSerializer):
    class ProjectItemSerializer(serializers.Serializer):
        class ListItemSerializer(serializers.Serializer):
            id = serializers.IntegerField(help_text="Project id")
            name = serializers.CharField(help_text="Project name")
            owner = serializers.IntegerField(help_text="Project creator")
            create_time = serializers.DateTimeField(help_text="Creation time")
            document_count = serializers.IntegerField(help_text="File count")
            project_type = serializers.IntegerField(help_text="Public project-1, private project-0")
            viewers_info = UserInfoSerializer(many=True)
        list = ListItemSerializer(many=True)
        total = serializers.IntegerField(help_text="Total count")
        page_num = serializers.IntegerField(help_text="Current page")
        page_size = serializers.IntegerField(help_text="Page size")

    data = ProjectItemSerializer()


class ProjectSerializer(serializers.ModelSerializer):
    # Tell serializers that this field is not from the model, but custom
    document_count = serializers.SerializerMethodField()
    viewers_info = serializers.SerializerMethodField()
    # Adjust the create_time field
    create_time = serializers.DateTimeField(
        format='%Y-%m-%d %H:%M:%S',  # No milliseconds
        read_only=True
    )

    class Meta:
        model = Project
        fields = ["id", "name", "owner", "viewers_info", "create_time", "document_count", "project_type"]

    def get_document_count(self, obj):
        # Note: The reason why we can get the doc object here is because related_name is defined in the Doc model
        # Exclude deleted documents
        return obj.doc.filter(is_deleted=False).count()

    def get_viewers_info(self, obj):
        # Note: This is a many-to-many relationship, use the field name to get all information
        return [
            {
                'id': viewer.id,
                'username': viewer.username,
            }
            for viewer in obj.viewers.all()
        ]
