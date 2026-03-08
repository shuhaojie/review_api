from django.urls import path
from api.app.user.views import (RegisterView, LoginView, VerifyCodeView, UserListView, UserDetailView,
                                GroupListView, GroupCreateView, GroupDetailView, UserCreateView, CurrentUserView)

urlpatterns = [
    path('/register', RegisterView.as_view(), name='register'),
    path('/verify_code', VerifyCodeView.as_view(), name='verify_code'),
    path('/login', LoginView.as_view(), name='login'),
    path('/list', UserListView.as_view(), name='list'),
    path('/me', CurrentUserView.as_view(), name='me'),  # Get current user information
    path('/<int:user_id>', UserDetailView.as_view(), name='user_detail'),  # User detail, update, delete
    path('/create', UserCreateView.as_view(), name='create'),  # Add route for creating users
    path('/group/list', GroupListView.as_view(), name='group_list'),
    path('/group/create', GroupCreateView.as_view(), name='group_create'),
    path('/group/<int:group_id>', GroupDetailView.as_view(), name='group_detail'),
]
