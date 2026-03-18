"""
URL configuration for RMCT project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from apps.simulations import views as simulation_views
from apps.simulations import latest_views as simulation_latest_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.users.urls")),
    path("", include("apps.labor.urls")),  # /api/labor, /api/labor/add, etc.
    path("api/", include("apps.rmct.urls")),
    path("api/", include("apps.equipment.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.operations.urls")),
    path("api/", include("apps.routing.urls")),
    path("api/", include("apps.ibom.urls")),
    path("api/organizations/", include("apps.organizations.urls")),
    # Lightweight simulation endpoint that uses the formula helpers in
    # apps.simulations.views. Safe to ignore if you prefer the
    # existing frontend-only calculation engine.
    path("api/simulations/rows", simulation_views.simulate_rows, name="simulate-rows"),
    path("api/simulations/full-calculate", simulation_latest_views.full_calculate_view, name="full-calculate"),
]
