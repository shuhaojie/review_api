from rest_framework import serializers


# 基础响应序列化器, POST/DELETE/PUT请求无需返回具体数据的, 可以使用序列化器
class BaseResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField(default=0, help_text="状态码：0-成功，非0-失败")
    success = serializers.BooleanField(default=True, help_text="是否成功")
    message = serializers.CharField(default="success", help_text="响应消息")

    class Meta:
        # 添加一个空的 Meta 类
        pass


# 数据响应序列化器, GET请求需要返回具体数据的, 一定要使用该序列化器
class DataResponseSerializer(BaseResponseSerializer):
    data = serializers.JSONField(required=False, allow_null=True, help_text="响应数据")
