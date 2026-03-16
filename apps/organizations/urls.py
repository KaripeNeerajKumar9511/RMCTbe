from django.urls import path
from . import views


urlpatterns = [

    path("", views.list_organizations, name="list_organizations"),

    path("create/", views.create_organization, name="create_organization"),

    path("<uuid:org_id>/", views.get_organization, name="get_organization"),

    path("<uuid:org_id>/update/", views.update_organization, name="update_organization"),

    path("<uuid:org_id>/delete/", views.delete_organization, name="delete_organization"),

]