from rest_framework import serializers


# 基础序列化器，自动添加中文错误消息
class BaseRequestValidationSerializer(serializers.Serializer):
    #  统一的中文错误消息配置
    default_error_messages = {
        'required': '{field_name} 字段为必填',
        'null': '{field_name} 字段不能为null',
        'blank': '{field_name} 字段不能为空',
        'invalid': '{field_name} 字段格式不正确',
        'max_length': '{field_name} 字段长度不能超过{max_length}个字符',
        'min_length': '{field_name} 字段长度不能少于{min_length}个字符',
        'max_value': '{field_name} 字段值不能大于{max_value}',
        'min_value': '{field_name} 字段值不能小于{min_value}',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_default_error_messages()

    def _apply_default_error_messages(self):
        """为所有字段应用默认错误消息"""
        for field_name, field in self.fields.items():
            # 为字段设置错误消息
            custom_messages = {}
            for error_key, error_template in self.default_error_messages.items():
                # 格式化错误消息，替换占位符
                formatted_message = error_template.format(
                    field_name=field_name,
                    max_length=getattr(field, 'max_length', ''),
                    min_length=getattr(field, 'min_length', ''),
                    max_value=getattr(field, 'max_value', ''),
                    min_value=getattr(field, 'min_value', ''),
                )
                custom_messages[error_key] = formatted_message

            # 更新字段的错误消息，但不覆盖已有的自定义消息
            field.error_messages.update(custom_messages)

            for validator in getattr(field, 'validators', []):
                if hasattr(validator, 'message'):
                    # 判断类型，匹配 min/max length/value 验证器
                    if validator.__class__.__name__ == 'MinLengthValidator':
                        validator.message = custom_messages.get('min_length')
                    elif validator.__class__.__name__ == 'MaxLengthValidator':
                        validator.message = custom_messages.get('max_length')
                    elif validator.__class__.__name__ == 'MinValueValidator':
                        validator.message = custom_messages.get('min_value')
                    elif validator.__class__.__name__ == 'MaxValueValidator':
                        validator.message = custom_messages.get('max_value')


# GET请求基本传参
class BaseGetRequestSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(required=False)
    page_size = serializers.IntegerField(required=False)
    q = serializers.CharField(required=False, help_text="搜索关键词，支持文档名称、项目名称、创建人用户名的模糊搜索")
