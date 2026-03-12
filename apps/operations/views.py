import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.rmct.models import RMCMModel
from apps.equipment.models import EquipmentGroup
from apps.labor.models import Labor
from apps.routing.models import Routing
from apps.products.models import Product

from .models import Operation


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return None


@csrf_exempt
@require_http_methods(['POST'])
def model_operations_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    owner = m.owner
    if owner is None or not hasattr(owner, "profile") or not getattr(owner.profile, "organization_id", None):
        return JsonResponse({'error': 'Owner organization not configured for model'}, status=400)

    org = owner.profile.organization

    op_id = data.get('id')
    product_id = data.get('product_id')
    product = get_object_or_404(Product, id=product_id)

    equip_id = data.get('equip_id')
    equipment_group = None
    if equip_id:
        equipment_group = EquipmentGroup.objects.filter(id=equip_id).first()

    operation_kwargs = {
        'organization': org,
        'product': product,
        'op_number': data.get('op_number', 1),
        'name': data.get('op_name', ''),
        'equipment_group': equipment_group,
        'percent_assign': data.get('pct_assigned', 100),
        'equipment_setup_per_lot': data.get('equip_setup_lot', 0),
        'equipment_run_per_piece': data.get('equip_run_piece', 0),
        'labor_setup_per_lot': data.get('labor_setup_lot', 0),
        'labor_run_per_piece': data.get('labor_run_piece', 0),
        'comments': '',
    }

    labor_group_id = data.get('labor_group_id')
    if labor_group_id:
        operation_kwargs['labor'] = Labor.objects.filter(id=labor_group_id).first()

    if op_id:
        operation_kwargs['id'] = op_id

    op = Operation.objects.create(**operation_kwargs)

    return JsonResponse({'id': str(op.id)}, status=201)


@csrf_exempt
@require_http_methods(['PATCH'])
def model_operations_update(request, model_id, op_id):
    get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    op = get_object_or_404(Operation, id=op_id)

    if 'op_name' in data:
        op.name = data['op_name']
    if 'op_number' in data:
        op.op_number = data['op_number']
    if 'pct_assigned' in data:
        op.percent_assign = data['pct_assigned']
    if 'equip_setup_lot' in data:
        op.equipment_setup_per_lot = data['equip_setup_lot']
    if 'equip_run_piece' in data:
        op.equipment_run_per_piece = data['equip_run_piece']
    if 'labor_setup_lot' in data:
        op.labor_setup_per_lot = data['labor_setup_lot']
    if 'labor_run_piece' in data:
        op.labor_run_per_piece = data['labor_run_piece']
    if 'equip_id' in data:
        equip_id = data.get('equip_id') or None
        if equip_id:
            op.equipment_group = EquipmentGroup.objects.filter(id=equip_id).first()
        else:
            op.equipment_group = None
    if 'labor_group_id' in data:
        labor_group_id = data.get('labor_group_id') or None
        if labor_group_id:
            op.labor = Labor.objects.filter(id=labor_group_id).first()
        else:
            op.labor = None

    op.save()

    return JsonResponse({})


@csrf_exempt
@require_http_methods(['DELETE'])
def model_operations_delete(request, model_id, op_id):
    get_object_or_404(RMCMModel, id=model_id)
    try:
        op = Operation.objects.get(id=op_id)
    except Operation.DoesNotExist:
        return JsonResponse({}, status=204)

    from django.utils import timezone

    now = timezone.now()
    op.deleted_at = now
    op.save()

    Routing.objects.filter(from_operation=op, deleted_at__isnull=True).update(deleted_at=now)

    return JsonResponse({}, status=204)
