from django.urls import path
from api.app.error.views import ErrorListView

urlpatterns = [
    path('', ErrorListView.as_view()),
]
