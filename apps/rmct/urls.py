from django.urls import path

from . import views
from apps.equipment import views as equipment_views
from apps.products import views as products_views
from apps.operations import views as operations_views
from apps.routing import views as routing_views
from apps.ibom import views as ibom_views

urlpatterns = [
    # Models
    path('models/', views.model_list_or_create),  # GET list, POST create (body has id)
    path('models/seed-demo/', views.seed_demo),
    path('models/<uuid:model_id>/', views.model_detail),  # GET one
    path('models/<uuid:model_id>/save/', views.model_save),  # PUT full model
    path('models/<uuid:model_id>/patch/', views.model_patch),
    path('models/<uuid:model_id>/delete/', views.model_delete),
    path('models/<uuid:model_id>/param-names/', views.model_param_names),
    path('models/<uuid:model_id>/param-names/upsert/', views.model_param_names_upsert),
    # Equipment (delegated to apps.equipment)
    path('models/<uuid:model_id>/equipment/', equipment_views.model_equipment_create),
    path('models/<uuid:model_id>/equipment/<str:equip_id>/', equipment_views.model_equipment_update),
    path('models/<uuid:model_id>/equipment/<str:equip_id>/delete/', equipment_views.model_equipment_delete),
    # Products (delegated to apps.products)
    path('models/<uuid:model_id>/products/', products_views.model_products_create),
    path('models/<uuid:model_id>/products/<str:product_id>/', products_views.model_products_update),
    path('models/<uuid:model_id>/products/<str:product_id>/delete/', products_views.model_products_delete),
    path('models/<uuid:model_id>/products/<str:product_id>/operations-and-routing/', products_views.model_products_clear_ops_routing),
    # Operations (delegated to apps.operations)
    path('models/<uuid:model_id>/operations/', operations_views.model_operations_create),
    path('models/<uuid:model_id>/operations/<str:op_id>/', operations_views.model_operations_update),
    path('models/<uuid:model_id>/operations/<str:op_id>/delete/', operations_views.model_operations_delete),
    # Routing (delegated to apps.routing)
    path('models/<uuid:model_id>/routing/', routing_views.model_routing_create),
    path('models/<uuid:model_id>/routing/set/', routing_views.model_routing_set),
    path('models/<uuid:model_id>/routing/<str:route_id>/', routing_views.model_routing_update),
    path('models/<uuid:model_id>/routing/<str:route_id>/delete/', routing_views.model_routing_delete),
    # IBOM (delegated to apps.ibom)
    path('models/<uuid:model_id>/ibom/', ibom_views.model_ibom_create),
    path('models/<uuid:model_id>/ibom/<str:parent_id>/', ibom_views.model_ibom_set_for_parent),
    path('models/<uuid:model_id>/ibom/entry/<str:entry_id>/', ibom_views.model_ibom_update),
    path('models/<uuid:model_id>/ibom/entry/<str:entry_id>/delete/', ibom_views.model_ibom_delete),
    # Versions
    path('models/<uuid:model_id>/versions/', views.version_list),
    path('models/<uuid:model_id>/versions/create/', views.version_create),
    path('models/<uuid:model_id>/versions/<uuid:version_id>/restore/', views.version_restore),
    path('versions/<uuid:version_id>/', views.version_snapshot),
    path('versions/<uuid:version_id>/patch/', views.version_patch),
    path('versions/<uuid:version_id>/delete/', views.version_delete),
    # Scenarios
    path('models/<uuid:model_id>/scenarios/', views.scenario_list_or_create),  # GET list, POST create
    path('models/<uuid:model_id>/scenarios/basecase/', views.scenario_ensure_basecase),
    path('models/<uuid:model_id>/scenarios/basecase/results/', views.scenario_basecase_results),  # GET + PUT
    path('scenarios/<uuid:scenario_id>/', views.scenario_patch),
    path('scenarios/<uuid:scenario_id>/delete/', views.scenario_delete),
    path('scenarios/<uuid:scenario_id>/changes/', views.scenario_upsert_change),
    path('scenarios/<uuid:scenario_id>/changes/<uuid:change_id>/delete/', views.scenario_remove_change),
    path('scenarios/<uuid:scenario_id>/results/', views.scenario_save_results),
]
