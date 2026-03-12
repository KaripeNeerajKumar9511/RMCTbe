import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.rmct.models import RMCMModel
from apps.products.models import Product
from apps.operations.models import Operation

from .models import Routing


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return None


def _get_or_create_product_from_model(model: RMCMModel, product_id: str) -> Product:
    """
    Ensure a Product row exists for the given model + product_id.

    If it doesn't exist yet, create it from the RMCMModel.products JSON list.
    """
    existing = Product.objects.filter(id=product_id).first()
    if existing:
        return existing

    # Find product data in the model snapshot
    snapshot_prod = next((p for p in (model.products or []) if str(p.get('id')) == str(product_id)), None)
    if not snapshot_prod:
        raise Product.DoesNotExist(f'Product {product_id} not found on model')

    owner = model.owner
    org = getattr(getattr(owner, "profile", None), "organization", None)

    prod_kwargs = {
        "id": snapshot_prod.get("id"),
        "organization": org,
        "name": snapshot_prod.get("name", "").upper(),
        "end_demand": snapshot_prod.get("demand", 0),
        "lot_size": snapshot_prod.get("lot_size", 1),
        "transfer_batch": snapshot_prod.get("tbatch_size", -1),
        "department_area": snapshot_prod.get("dept_code") or None,
        "demand_factor": snapshot_prod.get("demand_factor", 1),
        "lot_factor": snapshot_prod.get("lot_factor", 1),
        "variability_factor": snapshot_prod.get("var_factor", 1),
        "make_to_stock": snapshot_prod.get("make_to_stock", False),
        "gather_transfer_batches": snapshot_prod.get("gather_tbatches", False),
        "prod1": snapshot_prod.get("prod1", 0),
        "prod2": snapshot_prod.get("prod2", 0),
        "prod3": snapshot_prod.get("prod3", 0),
        "prod4": snapshot_prod.get("prod4", 0),
        "comments": snapshot_prod.get("comments", ""),
    }

    return Product.objects.create(**prod_kwargs)


def _get_or_create_operation_from_model(model: RMCMModel, product: Product, op_name: str) -> Operation:
    """
    Ensure an Operation row exists for the given model + product + op_name.

    If it doesn't exist yet, create it from the RMCMModel.operations JSON list.
    """
    existing = Operation.objects.filter(product=product, name=op_name, deleted_at__isnull=True).first()
    if existing:
        return existing

    snapshot_op = next(
        (o for o in (model.operations or [])
         if str(o.get("product_id")) == str(product.id) and o.get("op_name") == op_name),
        None,
    )
    if not snapshot_op:
        # For terminal/system operations like STOCK / SCRAP / DOCK, create a minimal
        # operation row even if it doesn't exist in the snapshot yet. Ensure we pick
        # an op_number that doesn't violate the unique (product, op_number) constraint.
        if op_name in ("STOCK", "SCRAP", "DOCK"):
            from django.db.models import Max

            owner = model.owner
            org = getattr(getattr(owner, "profile", None), "organization", None)
            max_num = (
                Operation.objects.filter(product=product)
                .aggregate(Max("op_number"))
                .get("op_number__max")
                or 0
            )
            default_number = max_num + 10
            op, _ = Operation.objects.get_or_create(
                product=product,
                name=op_name,
                defaults={
                    "organization": org,
                    "op_number": default_number,
                    "equipment_group": None,
                    "labor": None,
                    "percent_assign": 100,
                    "equipment_setup_per_lot": 0,
                    "equipment_run_per_piece": 0,
                    "labor_setup_per_lot": 0,
                    "labor_run_per_piece": 0,
                    "comments": "",
                },
            )
            return op
        raise Operation.DoesNotExist(f"Operation {op_name} not found on model for product {product.id}")

    owner = model.owner
    org = getattr(getattr(owner, "profile", None), "organization", None)

    equip_id = snapshot_op.get("equip_id")
    equipment_group = None
    if equip_id:
        equipment_group = Operation._meta.get_field("equipment_group").remote_field.model.objects.filter(id=equip_id).first()

    op_kwargs = {
        "id": snapshot_op.get("id"),
        "organization": org,
        "product": product,
        "op_number": snapshot_op.get("op_number", 1),
        "name": snapshot_op.get("op_name", ""),
        "equipment_group": equipment_group,
        "percent_assign": snapshot_op.get("pct_assigned", 100),
        "equipment_setup_per_lot": snapshot_op.get("equip_setup_lot", 0),
        "equipment_run_per_piece": snapshot_op.get("equip_run_piece", 0),
        "labor_setup_per_lot": snapshot_op.get("labor_setup_lot", 0),
        "labor_run_per_piece": snapshot_op.get("labor_run_piece", 0),
        "comments": "",
    }

    labor_group_id = snapshot_op.get("labor_group_id")
    if labor_group_id:
        labor_model = Operation._meta.get_field("labor").remote_field.model
        op_kwargs["labor"] = labor_model.objects.filter(id=labor_group_id).first()

    return Operation.objects.create(**op_kwargs)


@csrf_exempt
@require_http_methods(['POST'])
def model_routing_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    owner = m.owner
    if owner is None or not hasattr(owner, "profile") or not getattr(owner.profile, "organization_id", None):
        return JsonResponse({'error': 'Owner organization not configured for model'}, status=400)

    org = owner.profile.organization

    product_id = data.get('product_id')
    from_op_name = data.get('from_op_name')
    to_op_name = data.get('to_op_name')
    pct_routed = data.get('pct_routed', 100)

    if not product_id or not from_op_name or not to_op_name:
        return JsonResponse({'error': 'product_id, from_op_name and to_op_name are required'}, status=400)

    try:
        product = _get_or_create_product_from_model(m, product_id)
        from_op = _get_or_create_operation_from_model(m, product, from_op_name)
        to_op = _get_or_create_operation_from_model(m, product, to_op_name)
    except (Product.DoesNotExist, Operation.DoesNotExist) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # Upsert routing path: unique on (from_operation, to_operation)
    routing_defaults = {
        'organization': org,
        'product': product,
        'probability': pct_routed,
        'deleted_at': None,
    }
    r, created = Routing.objects.update_or_create(
        from_operation=from_op,
        to_operation=to_op,
        defaults=routing_defaults,
    )

    return JsonResponse({'id': str(r.id)}, status=201 if created else 200)


@csrf_exempt
@require_http_methods(['PUT'])
def model_routing_set(request, model_id):
    """PUT /api/models/:id/routing — replace routing for a product (body: productId, entries)."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    owner = m.owner
    if owner is None or not hasattr(owner, "profile") or not getattr(owner.profile, "organization_id", None):
        return JsonResponse({'error': 'Owner organization not configured for model'}, status=400)

    org = owner.profile.organization

    product_id = data.get('productId') or data.get('product_id')
    entries = data.get('entries', [])
    if product_id is None:
        return JsonResponse({'error': 'productId required'}, status=400)

    try:
        product = _get_or_create_product_from_model(m, product_id)
    except Product.DoesNotExist as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    from django.utils import timezone

    now = timezone.now()
    Routing.objects.filter(product=product, deleted_at__isnull=True).update(deleted_at=now)

    for entry in entries:
        from_op_name = entry.get('from_op_name')
        to_op_name = entry.get('to_op_name')
        pct_routed = entry.get('pct_routed', 100)
        try:
            from_op = _get_or_create_operation_from_model(m, product, from_op_name)
            to_op = _get_or_create_operation_from_model(m, product, to_op_name)
        except Operation.DoesNotExist as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        Routing.objects.create(
            organization=org,
            product=product,
            from_operation=from_op,
            to_operation=to_op,
            probability=pct_routed,
        )

    return JsonResponse({})


@csrf_exempt
@require_http_methods(['PATCH'])
def model_routing_update(request, model_id, route_id):
    get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    r = get_object_or_404(Routing, id=route_id)

    if 'pct_routed' in data:
        r.probability = data['pct_routed']

    r.save()

    return JsonResponse({})


@csrf_exempt
@require_http_methods(['DELETE'])
def model_routing_delete(request, model_id, route_id):
    get_object_or_404(RMCMModel, id=model_id)
    try:
        r = Routing.objects.get(id=route_id)
    except Routing.DoesNotExist:
        return JsonResponse({}, status=204)

    from django.utils import timezone

    r.deleted_at = timezone.now()
    r.save()

    return JsonResponse({}, status=204)
