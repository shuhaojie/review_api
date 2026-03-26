from django.urls import path
from api.app.project.views import ProjectListView, ProjectDetailView

urlpatterns = [
    path('', ProjectListView.as_view()),
    path('<int:pk>', ProjectDetailView.as_view()),
]
