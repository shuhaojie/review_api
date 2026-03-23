from rest_framework import serializers


# Base serializer that automatically applies field-level error messages
class BaseRequestValidationSerializer(serializers.Serializer):
    # Unified error message templates
    default_error_messages = {
        'required': '{field_name} is required.',
        'null': '{field_name} may not be null.',
        'blank': '{field_name} may not be blank.',
        'invalid': '{field_name} has an invalid format.',
        'max_length': '{field_name} must be at most {max_length} characters.',
        'min_length': '{field_name} must be at least {min_length} characters.',
        'max_value': '{field_name} must be no greater than {max_value}.',
        'min_value': '{field_name} must be no less than {min_value}.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_default_error_messages()

    def _apply_default_error_messages(self):
        """Apply default error messages to all fields."""
        for field_name, field in self.fields.items():
            custom_messages = {}
            for error_key, error_template in self.default_error_messages.items():
                formatted_message = error_template.format(
                    field_name=field_name,
                    max_length=getattr(field, 'max_length', ''),
                    min_length=getattr(field, 'min_length', ''),
                    max_value=getattr(field, 'max_value', ''),
                    min_value=getattr(field, 'min_value', ''),
                )
                custom_messages[error_key] = formatted_message

            # Update field error messages without overriding existing custom ones
            field.error_messages.update(custom_messages)

            for validator in getattr(field, 'validators', []):
                if hasattr(validator, 'message'):
                    if validator.__class__.__name__ == 'MinLengthValidator':
                        validator.message = custom_messages.get('min_length')
                    elif validator.__class__.__name__ == 'MaxLengthValidator':
                        validator.message = custom_messages.get('max_length')
                    elif validator.__class__.__name__ == 'MinValueValidator':
                        validator.message = custom_messages.get('min_value')
                    elif validator.__class__.__name__ == 'MaxValueValidator':
                        validator.message = custom_messages.get('max_value')


# Base serializer for GET requests with pagination and search
class BaseGetRequestSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(required=False)
    page_size = serializers.IntegerField(required=False)
    q = serializers.CharField(required=False, help_text="Search keyword. Supports fuzzy matching on document name, project name, and creator username.")
