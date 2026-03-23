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
        help_text="List of files to upload"
    )

    def validate_files(self, files):
        """Validate the uploaded file list."""
        if not files:
            raise serializers.ValidationError("At least one file is required.")

        if len(files) > env.MAX_UPLOAD_FILES:
            raise serializers.ValidationError(f"You may upload at most {env.MAX_UPLOAD_FILES} files at a time.")

        for file in files:
            self._validate_single_file(file)

        return files

    @staticmethod
    def _validate_single_file(file):
        """Validate a single uploaded file."""
        if not isinstance(file, UploadedFile):
            raise serializers.ValidationError("Invalid file format.")

        max_size = int(env.MAX_FILE_SIZE) * 1024 * 1024
        if file.size > max_size:
            raise serializers.ValidationError(
                f"File '{file.name}' exceeds the {env.MAX_FILE_SIZE}MB size limit."
            )

        allowed_extensions = ['.docx', '.pdf']
        file_extension = os.path.splitext(file.name)[1].lower()

        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File '{file.name}' has an unsupported format. Only {', '.join(allowed_extensions)} files are allowed."
            )

        # Additional MIME type validation
        allowed_content_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'  # Legacy Word format sometimes submitted alongside docx
        ]

        if hasattr(file, 'content_type') and file.content_type:
            if file.content_type not in allowed_content_types:
                raise serializers.ValidationError(
                    f"File '{file.name}' has an unsupported content type."
                )

    def create(self, validated_data):
        files = validated_data.get('files', [])
        file_info_list = []
        for file in files:
            file_name = file.name
            file_extension = os.path.splitext(file_name)[1].lower()
            f_uuid = str(uuid.uuid4())
            file_uuid = f"{f_uuid}{file_extension}"
            # Must use a relative path here; Django raises an error for absolute paths
            save_path = f"data/upload/{file_uuid}"
            default_storage.save(save_path, file)

            file_info_list.append({
                'file_uuid': file_uuid,
                'file_name': file_name
            })
        return file_info_list


class DocTaskRequestSerializer(BaseRequestValidationSerializer):
    class FileItemSerializer(BaseRequestValidationSerializer):
        """Serializer for a single file entry."""
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
            raise serializers.ValidationError(f"Project with id {value} does not exist.")

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        project_id = validated_data.get('project_id')
        file_list = validated_data.get('file_list')
        project = Project.objects.get(id=project_id)
        created_documents, file_info_list = [], []
        for f in file_list:
            file_uuid = f['file_uuid']
            file_name = f['file_name']
            doc = Doc.objects.create(
                file_name=file_name,
                file_uuid=file_uuid,
                owner=user,
                project_id=project,
                status=0  # Queued
            )
            DocStatus.objects.create(
                doc_id=doc.id,
                parse_status=0  # Queued
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
