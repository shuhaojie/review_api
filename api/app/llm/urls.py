from django.urls import path

from api.app.llm.views import (PromptListView, PromptDetailView, ProviderListView, ProviderDetailView,
                               TestListView, TestSampleView, SetDefaultView, PromptBatchDeleteView,
                               ExportLLMTestView)

urlpatterns = [
    path('/prompt', PromptListView.as_view()),
    path('/prompt/<int:pk>', PromptDetailView.as_view()),
    path('/prompt/batch-delete', PromptBatchDeleteView.as_view()),  # 新增批量删除

    path('/provider', ProviderListView.as_view()),
    path('/provider/<int:pk>', ProviderDetailView.as_view()),

    path('/test', TestListView.as_view()),  # 测试历史
    path('/test/export', ExportLLMTestView.as_view()),  # 新增导出接口

    # 将参数设为系统默认
    path('/set-default/<int:pk>', SetDefaultView.as_view()),
]
