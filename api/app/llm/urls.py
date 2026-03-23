from django.urls import path

from api.app.llm.views import (PromptListView, PromptDetailView, ProviderListView, ProviderDetailView,
                               TestListView, TestSampleView, SetDefaultView, PromptBatchDeleteView,
                               ExportLLMTestView)

urlpatterns = [
    path('/prompt', PromptListView.as_view()),
    path('/prompt/<int:pk>', PromptDetailView.as_view()),
    path('/prompt/batch-delete', PromptBatchDeleteView.as_view()),

    path('/provider', ProviderListView.as_view()),
    path('/provider/<int:pk>', ProviderDetailView.as_view()),

    path('/test', TestListView.as_view()),  # Test history
    path('/test/export', ExportLLMTestView.as_view()),  # Export test results

    # Set the given item as the system default
    path('/set-default/<int:pk>', SetDefaultView.as_view()),
]
