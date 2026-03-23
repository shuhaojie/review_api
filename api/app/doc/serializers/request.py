# serializers.py
import os
import uuid
from rest_framework import serializers
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from api.settings.config import env
from api.app.doc.models import Doc, DocStatus
from api.app.project.models import Project
from api.app.base.serializers.request import BaseRequestValidationSerializer


class MultiFileUploadRequestSerializer(BaseRequestValidationSerializer):
    files = serializers.ListField(
        child=serializers.FileField(max_length=100, allow_empty_file=False),
        help_text="文件列表"
    )

    def validate_files(self, files):
        """验证文件列表"""
        if not files:
            raise serializers.ValidationError("至少需要上传一个文件")

        if len(files) > env.MAX_UPLOAD_FILES:
            raise serializers.ValidationError(f"一次最多上传{env.MAX_UPLOAD_FILES}个文件")

        # 验证每个文件
        for file in files:
            self._validate_single_file(file)

        return files

    @staticmethod
    def _validate_single_file(file):
        """验证单个文件"""
        if not isinstance(file, UploadedFile):
            raise serializers.ValidationError("无效的文件格式")

        # 验证文件大小 (5MB = 5 * 1024 * 1024 bytes)
        max_size = int(env.MAX_FILE_SIZE) * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                f"文件:{file.name}，大小超过{env.MAX_FILE_SIZE}MB限制"
            )

        # 验证文件扩展名
        allowed_extensions = ['.docx', '.pdf']
        file_extension = os.path.splitext(file.name)[1].lower()

        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"文件:{file.name}，格式不支持，只允许上传 {', '.join(allowed_extensions)} 格式"
            )

        # 验证文件内容类型（额外的安全校验）
        allowed_content_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'  # 虽然你只要求docx，但有时旧版word也会被上传
        ]

        if hasattr(file, 'content_type') and file.content_type:
            if file.content_type not in allowed_content_types:
                raise serializers.ValidationError(
                    f"文件:{file.name}，内容类型不被支持"
                )

    def create(self, validated_data):
        files = validated_data.get('files', [])
        # 获取项目
        created_documents, file_info_list = [], []
        for file in files:
            # 生成文件信息
            file_name = file.name
            file_extension = os.path.splitext(file_name)[1].lower()
            f_uuid = str(uuid.uuid4())
            # 生成唯一文件名
            file_uuid = f"{f_uuid}{file_extension}"
            # 注意这里不能存绝对路径, 否则Django会报错
            save_path = f"data/upload/{file_uuid}"
            default_storage.save(save_path, file)

            file_info_list.append({
                'file_uuid': file_uuid,
                'file_name': file_name
            })
        return file_info_list


class DocTaskRequestSerializer(BaseRequestValidationSerializer):
    class FileItemSerializer(BaseRequestValidationSerializer):
        """文件项序列化器"""
        file_name = serializers.CharField()
        file_uuid = serializers.CharField()

    project_id = serializers.IntegerField()
    file_list = serializers.ListField(
        child=FileItemSerializer()
    )

    def validate_project_id(self, value):
        try:
            Project.objects.get(id=value, is_deleted=False)
        except Project.DoesNotExist:
            raise serializers.ValidationError(f"项目id {value} 不存在")

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        project_id = validated_data.get('project_id')
        file_list = validated_data.get('file_list')
        project = Project.objects.get(id=project_id)
        created_documents, file_info_list = [], []
        for f in file_list:
            # 生成文件信息
            file_uuid = f['file_uuid']
            file_name = f['file_name']
            # 创建文档记录
            doc = Doc.objects.create(
                file_name=file_name,
                file_uuid=file_uuid,
                owner=user,
                project_id=project,
                status=0  # 排队中
            )
            DocStatus.objects.create(
                doc_id=doc.id,
                parse_status=0  # 排队中
            )
            created_documents.append(doc)
            file_info_list.append({
                'doc_id': doc.id,
                'file_name': file_name,
                'file_uuid': file_uuid
            })
        return {
            'documents': created_documents,
            'file_info': file_info_list
        }


class SingleDocRequestSerializer(BaseRequestValidationSerializer):
    doc_id = serializers.IntegerField()
