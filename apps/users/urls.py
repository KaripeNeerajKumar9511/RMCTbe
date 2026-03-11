from django.urls import path
from . import views

urlpatterns = [
    path("api/csrf/", views.csrf_cookie),
    path("api/signup/", views.signup),
    path("api/login/", views.login_view),
    path("api/profile/", views.profile),
    path("api/logout/", views.logout_view),
]
