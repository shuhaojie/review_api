from django.urls import path

from api.app.llm.views import (PromptListView, PromptDetailView, ProviderListView, ProviderDetailView,
                               TestListView, TestSampleView, TestSampleDetailView, SetDefaultView,
                               PromptBatchDeleteView, ExportLLMTestView)

urlpatterns = [
    # Prompts
    path('prompts', PromptListView.as_view()),
    path('prompts/batch-delete', PromptBatchDeleteView.as_view()),
    path('prompts/<int:pk>', PromptDetailView.as_view()),

    # LLM Providers
    path('providers', ProviderListView.as_view()),
    path('providers/<int:pk>', ProviderDetailView.as_view()),

    # LLM Tests
    path('tests', TestListView.as_view()),
    path('tests/export', ExportLLMTestView.as_view()),
    path('tests/<int:pk>/set-default', SetDefaultView.as_view()),

    # Test samples
    path('test-samples', TestSampleView.as_view()),
    path('test-samples/<int:pk>', TestSampleDetailView.as_view()),
]
