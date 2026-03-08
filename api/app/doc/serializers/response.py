from rest_framework import serializers
from api.app.doc.models import Doc
from api.app.base.serializers.response import BaseResponseSerializer


class DocMetaSerializer(serializers.ModelSerializer):
    # 对create_time字段进行调整
    create_time = serializers.DateTimeField(
        format='%Y-%m-%d %H:%M:%S',  # 无毫秒
        read_only=True
    )
    # 告诉serializers, 这个字段不是模型的, 而是自定义的
    error_count = serializers.SerializerMethodField()
    # 添加项目名称字段
    project_name = serializers.SerializerMethodField()
    # 将owner从id改为username
    owner = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Doc
        fields = ["id", "file_name", "status", "create_time", "owner", "error_count", "project_name"]

    def get_error_count(self, obj):
        # 注意: 这里只所以可以获取doc对象, 是因为Doc模型里定义了related_name
        return obj.doc_text_error.count() + obj.doc_financial_error.count()

    def get_project_name(self, obj):
        # 获取项目名称
        return obj.project_id.name


class DocListResponseSerializer(BaseResponseSerializer):
    data = DocMetaSerializer(many=True)


class MultiFileUploadResponseSerializer(BaseResponseSerializer):
    class FileUploadItemResponseSerializer(serializers.Serializer):
        file_name = serializers.CharField()
        file_uuid = serializers.CharField()

    data = FileUploadItemResponseSerializer(many=True)
