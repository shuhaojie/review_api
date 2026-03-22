from rest_framework import serializers


class ErrorListRequestSerializer(serializers.Serializer):
    doc_id = serializers.IntegerField(required=True, help_text="文档id")
