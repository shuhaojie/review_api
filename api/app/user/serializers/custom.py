from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Only override get_token to put custom claims into payload"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Key: Everything added here will be in the token payload
        token['is_admin'] = user.is_superuser
        return token

    # Optional: Also override validate to make the login interface return body also include is_admin
    def validate(self, attrs):
        data = super().validate(attrs)
        data['is_admin'] = self.user.is_superuser
        return data
