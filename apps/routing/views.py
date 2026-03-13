import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from apps.rmct.models import RMCMModel
from apps.products.models import Product
from apps.operations.models import Operation
from .models import Routing


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return None


def _get_org_from_model(model):
    owner = model.owner
    if owner is None or not hasattr(owner, "profile") or not owner.profile.organization:
        return None
    return owner.profile.organization


def _get_or_create_product_from_model(model, product_id):
    existing = Product.objects.filter(id=product_id).first()
    if existing:
        return existing

    snapshot_prod = next(
        (p for p in (model.products or []) if str(p.get("id")) == str(product_id)),
        None,
    )

    if not snapshot_prod:
        raise Product.DoesNotExist(f"Product {product_id} not found on model")

    org = _get_org_from_model(model)

    return Product.objects.create(
        id=snapshot_prod.get("id"),
        organization=org,
        name=snapshot_prod.get("name", "").upper(),
        end_demand=snapshot_prod.get("demand", 0),
        lot_size=snapshot_prod.get("lot_size", 1),
        transfer_batch=snapshot_prod.get("tbatch_size", -1),
        department_area=snapshot_prod.get("dept_code") or None,
        demand_factor=snapshot_prod.get("demand_factor", 1),
        lot_factor=snapshot_prod.get("lot_factor", 1),
        variability_factor=snapshot_prod.get("var_factor", 1),
        make_to_stock=snapshot_prod.get("make_to_stock", False),
        gather_transfer_batches=snapshot_prod.get("gather_tbatches", False),
        prod1=snapshot_prod.get("prod1", 0),
        prod2=snapshot_prod.get("prod2", 0),
        prod3=snapshot_prod.get("prod3", 0),
        prod4=snapshot_prod.get("prod4", 0),
        comments=snapshot_prod.get("comments", ""),
    )


def _get_or_create_operation_from_model(model, product, op_name):
    existing = Operation.objects.filter(
        product=product,
        name=op_name,
        deleted_at__isnull=True,
    ).first()

    if existing:
        return existing

    snapshot_op = next(
        (
            o
            for o in (model.operations or [])
            if str(o.get("product_id")) == str(product.id)
            and o.get("op_name") == op_name
        ),
        None,
    )

    org = _get_org_from_model(model)

    if not snapshot_op:

        if op_name in ("STOCK", "SCRAP", "DOCK"):

            from django.db.models import Max

            max_num = (
                Operation.objects.filter(product=product)
                .aggregate(Max("op_number"))
                .get("op_number__max")
                or 0
            )

            return Operation.objects.create(
                organization=org,
                product=product,
                name=op_name,
                op_number=max_num + 10,
                percent_assign=100,
                equipment_setup_per_lot=0,
                equipment_run_per_piece=0,
                labor_setup_per_lot=0,
                labor_run_per_piece=0,
            )

        raise Operation.DoesNotExist(
            f"Operation {op_name} not found for product {product.id}"
        )

    equip_id = snapshot_op.get("equip_id")
    equipment_group = None

    if equip_id:
        equipment_group = (
            Operation._meta.get_field("equipment_group")
            .remote_field.model.objects.filter(id=equip_id)
            .first()
        )

    labor_group = None
    labor_group_id = snapshot_op.get("labor_group_id")

    if labor_group_id:
        labor_group = (
            Operation._meta.get_field("labor")
            .remote_field.model.objects.filter(id=labor_group_id)
            .first()
        )

    return Operation.objects.create(
        id=snapshot_op.get("id"),
        organization=org,
        product=product,
        op_number=snapshot_op.get("op_number", 1),
        name=snapshot_op.get("op_name", ""),
        equipment_group=equipment_group,
        labor=labor_group,
        percent_assign=snapshot_op.get("pct_assigned", 100),
        equipment_setup_per_lot=snapshot_op.get("equip_setup_lot", 0),
        equipment_run_per_piece=snapshot_op.get("equip_run_piece", 0),
        labor_setup_per_lot=snapshot_op.get("labor_setup_lot", 0),
        labor_run_per_piece=snapshot_op.get("labor_run_piece", 0),
    )


@csrf_exempt
@require_http_methods(["POST"])
def model_routing_create(request, model_id):

    m = get_object_or_404(RMCMModel, id=model_id)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    org = _get_org_from_model(m)
    if not org:
        return JsonResponse(
            {"error": "Owner organization not configured"}, status=400
        )

    product_id = data.get("product_id")
    from_op_name = data.get("from_op_name")
    to_op_name = data.get("to_op_name")
    pct_routed = data.get("pct_routed", 100)

    if pct_routed < 0 or pct_routed > 100:
        return JsonResponse({"error": "pct_routed must be 0-100"}, status=400)

    if not product_id or not from_op_name or not to_op_name:
        return JsonResponse(
            {"error": "product_id, from_op_name and to_op_name required"},
            status=400,
        )

    try:
        product = _get_or_create_product_from_model(m, product_id)
        from_op = _get_or_create_operation_from_model(m, product, from_op_name)
        to_op = _get_or_create_operation_from_model(m, product, to_op_name)
    except (Product.DoesNotExist, Operation.DoesNotExist) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    # Reuse any existing route (including previously soft-deleted ones) to
    # avoid violating the unique_operation_path DB constraint.
    routing = (
        Routing.objects.filter(
            product=product,
            from_operation=from_op,
            to_operation=to_op,
        )
        .order_by("-deleted_at")
        .first()
    )

    if routing:
        # "Undelete" if it was soft-deleted and update probability
        routing.probability = pct_routed
        routing.deleted_at = None
        routing.save()
        created = False
    else:
        routing = Routing.objects.create(
            organization=org,
            product=product,
            from_operation=from_op,
            to_operation=to_op,
            probability=pct_routed,
        )
        created = True

    return JsonResponse({"id": str(routing.id)}, status=201 if created else 200)


@csrf_exempt
@require_http_methods(["PUT"])
@transaction.atomic
def model_routing_set(request, model_id):

    m = get_object_or_404(RMCMModel, id=model_id)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    org = _get_org_from_model(m)
    if not org:
        return JsonResponse(
            {"error": "Owner organization not configured"}, status=400
        )

    product_id = data.get("productId") or data.get("product_id")
    entries = data.get("entries", [])

    if product_id is None:
        return JsonResponse({"error": "productId required"}, status=400)

    try:
        product = _get_or_create_product_from_model(m, product_id)
    except Product.DoesNotExist as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    Routing.objects.filter(
        product=product,
        organization=org,
        deleted_at__isnull=True,
    ).update(deleted_at=timezone.now())

    for entry in entries:

        from_op = _get_or_create_operation_from_model(
            m, product, entry.get("from_op_name")
        )

        to_op = _get_or_create_operation_from_model(
            m, product, entry.get("to_op_name")
        )

        pct_routed = entry.get("pct_routed", 100)

        if pct_routed < 0 or pct_routed > 100:
            return JsonResponse(
                {"error": "pct_routed must be 0-100"}, status=400
            )

        Routing.objects.create(
            organization=org,
            product=product,
            from_operation=from_op,
            to_operation=to_op,
            probability=pct_routed,
        )

    return JsonResponse({})


@csrf_exempt
@require_http_methods(["PATCH"])
def model_routing_update(request, model_id, route_id):

    m = get_object_or_404(RMCMModel, id=model_id)
    org = _get_org_from_model(m)

    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    routing = get_object_or_404(
        Routing,
        id=route_id,
        organization=org,
        deleted_at__isnull=True,
    )

    # Update probability (% routed)
    if "pct_routed" in data:

        pct = data["pct_routed"]

        if pct < 0 or pct > 100:
            return JsonResponse(
                {"error": "pct_routed must be 0-100"}, status=400
            )

        routing.probability = pct

    # Allow changing the destination operation for a route
    if "to_op_name" in data:
        try:
            product = routing.product
            to_op = _get_or_create_operation_from_model(
                m, product, data.get("to_op_name")
            )
        except Operation.DoesNotExist as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        routing.to_operation = to_op

    routing.save()

    return JsonResponse({})


@csrf_exempt
@require_http_methods(["DELETE"])
def model_routing_delete(request, model_id, route_id):

    m = get_object_or_404(RMCMModel, id=model_id)
    org = _get_org_from_model(m)

    routing = Routing.objects.filter(
        id=route_id,
        organization=org,
        deleted_at__isnull=True,
    ).first()

    if not routing:
        return JsonResponse({}, status=204)

    routing.deleted_at = timezone.now()
    routing.save()

    return JsonResponse({}, status=204)