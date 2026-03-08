from rest_framework import serializers
from api.app.base.serializers.response import BaseResponseSerializer
from api.app.error.models import TextError, FinancialError


class ErrorListRequestSerializer(serializers.Serializer):
    doc_id = serializers.IntegerField(required=True, help_text="文档id")


class ErrorItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextError
        fields = '__all__'

class FinanceErrorItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialError
        fields = '__all__'


class ErrorListResponseSerializer(BaseResponseSerializer):
    data = ErrorItemSerializer(many=True)
    finance_data = FinanceErrorItemSerializer(many=True)
