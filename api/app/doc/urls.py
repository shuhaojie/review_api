from django.urls import path
from api.app.doc.views import FileUploadView, DocListView, FileTaskView, RetryTaskView, DocDownloadView, DocDetailView

urlpatterns = [
    path('', DocListView.as_view()),                          # GET  /docs
    path('upload', FileUploadView.as_view()),                 # POST /docs/upload
    path('tasks', FileTaskView.as_view()),                    # POST /docs/tasks
    path('<int:pk>', DocDetailView.as_view()),                 # GET  /docs/{id}
    path('<int:pk>/download', DocDownloadView.as_view()),     # GET  /docs/{id}/download
    path('<int:pk>/retry', RetryTaskView.as_view()),          # POST /docs/{id}/retry
]
