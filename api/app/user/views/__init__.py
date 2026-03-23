from api.app.user.views.auth import RegisterView, VerifyCodeView, LoginView
from api.app.user.views.user import UserListView, UserCreateView, CurrentUserView, UserDetailView
from api.app.user.views.group import GroupListView, GroupDetailView, GroupCreateView

__all__ = [
    'RegisterView', 'VerifyCodeView', 'LoginView',
    'UserListView', 'UserCreateView', 'CurrentUserView', 'UserDetailView',
    'GroupListView', 'GroupDetailView', 'GroupCreateView',
]
