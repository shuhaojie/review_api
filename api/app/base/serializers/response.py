from rest_framework import serializers


# Use for POST/DELETE/PUT responses that don't return data payloads
class BaseResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=0, help_text="Status code: 0 = success, non-zero = failure")
    success = serializers.BooleanField(default=True, help_text="Whether the request succeeded")
    message = serializers.CharField(default="success", help_text="Response message")

    class Meta:
        pass


# Use for GET responses that return a data payload
class DataResponseSerializer(BaseResponseSerializer):
    data = serializers.JSONField(required=False, allow_null=True, help_text="Response data")
