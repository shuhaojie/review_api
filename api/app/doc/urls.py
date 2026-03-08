from django.urls import path
from api.app.doc.views import FileUploadView, DocListView, FileTaskView, RetryTaskView, DocDownloadView, DocDetailView

urlpatterns = [
    path('/upload', FileUploadView.as_view()),
    path('/task', FileTaskView.as_view()),
    path('/list', DocListView.as_view()),
    path('/retry', RetryTaskView.as_view()),
    path('/download', DocDownloadView.as_view()),
    path('/detail', DocDetailView.as_view()),
]
