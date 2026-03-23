from rest_framework import serializers
from api.app.doc.models import Doc
from api.app.base.serializers.response import BaseResponseSerializer


class DocMetaSerializer(serializers.ModelSerializer):
    # Format create_time without milliseconds
    create_time = serializers.DateTimeField(
        format='%Y-%m-%d %H:%M:%S',
        read_only=True
    )
    # Computed field, not from the model directly
    error_count = serializers.SerializerMethodField()
    # Computed field for project name
    project_name = serializers.SerializerMethodField()
    # Return username instead of user id
    owner = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Doc
        fields = ["id", "file_name", "status", "create_time", "owner", "error_count", "project_name"]

    def get_error_count(self, obj):
        # Accessible via related_name defined on the Doc model
        return obj.doc_text_error.count() + obj.doc_financial_error.count()

    def get_project_name(self, obj):
        return obj.project_id.name


class DocListResponseSerializer(BaseResponseSerializer):
    data = DocMetaSerializer(many=True)


class MultiFileUploadResponseSerializer(BaseResponseSerializer):
    class FileUploadItemResponseSerializer(serializers.Serializer):
        file_name = serializers.CharField()
        file_uuid = serializers.CharField()

    data = FileUploadItemResponseSerializer(many=True)
