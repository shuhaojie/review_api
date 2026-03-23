from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="Project API Documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@yourdomain.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

api_urlpatterns = [
    path('user', include('api.app.user.urls')),
    path('project', include('api.app.project.urls')),
    path('doc', include('api.app.doc.urls')),
    path("llm", include("api.app.llm.urls")),
    path("error", include("api.app.error.urls")),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', include('health_check.urls')),

    # Unified api prefix wrapping
    path('api/', include(api_urlpatterns)),

    # Swagger documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

handler404 = "api.app.base.exceptions.django_404_handler"
handler500 = "api.app.base.exceptions.django_500_handler"

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
