from django.urls import path
from api.app.user.views import (RegisterView, LoginView, VerifyCodeView, UserListView,
                                UserDetailView, GroupListView, GroupDetailView, CurrentUserView)

urlpatterns = [
    # Auth (action-oriented endpoints are acceptable for auth flows)
    path('register', RegisterView.as_view(), name='register'),
    path('verify-code', VerifyCodeView.as_view(), name='verify_code'),
    path('login', LoginView.as_view(), name='login'),

    # User resource: GET /users → list, POST /users → create
    path('', UserListView.as_view(), name='user_list'),
    path('me', CurrentUserView.as_view(), name='me'),
    path('<int:user_id>', UserDetailView.as_view(), name='user_detail'),

    # Group sub-resource: GET /users/groups → list, POST /users/groups → create
    path('groups', GroupListView.as_view(), name='group_list'),
    path('groups/<int:group_id>', GroupDetailView.as_view(), name='group_detail'),
]

