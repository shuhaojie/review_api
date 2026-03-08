from django.urls import path
from api.app.error.views import ErrorListView

urlpatterns = [
    path('/list', ErrorListView.as_view()),
]
