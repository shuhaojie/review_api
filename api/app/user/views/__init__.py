from api.app.user.views.auth import RegisterView, VerifyCodeView, LoginView
from api.app.user.views.user import UserListView, CurrentUserView, UserDetailView
from api.app.user.views.group import GroupListView, GroupDetailView

__all__ = [
    'RegisterView', 'VerifyCodeView', 'LoginView',
    'UserListView', 'CurrentUserView', 'UserDetailView',
    'GroupListView', 'GroupDetailView',
]
