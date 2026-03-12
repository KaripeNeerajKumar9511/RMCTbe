import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.rmct.models import RMCMModel
from apps.labor.models import Labor

from .models import EquipmentGroup


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return None


@csrf_exempt
@require_http_methods(['POST'])
def model_equipment_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    owner = m.owner
    if owner is None or not hasattr(owner, "profile") or not getattr(owner.profile, "organization_id", None):
        return JsonResponse({'error': 'Owner organization not configured for model'}, status=400)

    org = owner.profile.organization

    equip_id = data.get('id')
    equip_kwargs = {
        'organization': org,
        'name': data.get('name', '').upper(),
        'count': data.get('count', 1),
        'mttf_minutes': data.get('mttf', 0),
        'mttr_minutes': data.get('mttr', 0),
        'overtime_percent': data.get('overtime_pct', 0),
        'department_area': data.get('dept_code') or None,
        'out_of_area_equipment': data.get('out_of_area', False),
        'percent_time_unavailable': data.get('unavail_pct', 0),
        'setup_factor': data.get('setup_factor', 1),
        'run_factor': data.get('run_factor', 1),
        'variability_factor': data.get('var_factor', 1),
        'eq1': data.get('eq1', 0),
        'eq2': data.get('eq2', 0),
        'eq3': data.get('eq3', 0),
        'eq4': data.get('eq4', 0),
        'comments': data.get('comments', ''),
    }

    labor_group_id = data.get('labor_group_id')
    if labor_group_id:
        equip_kwargs['labor_group_id'] = labor_group_id

    equip_type = (data.get('equip_type') or 'standard').lower()
    equip_kwargs['equipment_type'] = 'Delay' if equip_type == 'delay' else 'Standard'

    if equip_id:
        equip_kwargs['id'] = equip_id

    eq = EquipmentGroup.objects.create(**equip_kwargs)

    return JsonResponse({'id': str(eq.id)}, status=201)


@csrf_exempt
@require_http_methods(['PATCH'])
def model_equipment_update(request, model_id, equip_id):
    get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    eq = get_object_or_404(EquipmentGroup, id=equip_id)

    if 'name' in data:
        eq.name = data['name']
    if 'count' in data:
        eq.count = data['count']
    if 'mttf' in data:
        eq.mttf_minutes = data['mttf']
    if 'mttr' in data:
        eq.mttr_minutes = data['mttr']
    if 'overtime_pct' in data:
        eq.overtime_percent = data['overtime_pct']
    if 'dept_code' in data:
        eq.department_area = data['dept_code'] or None
    if 'out_of_area' in data:
        eq.out_of_area_equipment = data['out_of_area']
    if 'unavail_pct' in data:
        eq.percent_time_unavailable = data['unavail_pct']
    if 'setup_factor' in data:
        eq.setup_factor = data['setup_factor']
    if 'run_factor' in data:
        eq.run_factor = data['run_factor']
    if 'var_factor' in data:
        eq.variability_factor = data['var_factor']
    for key in ('eq1', 'eq2', 'eq3', 'eq4'):
        if key in data:
            setattr(eq, key, data[key])
    if 'comments' in data:
        eq.comments = data['comments']
    if 'labor_group_id' in data:
        labor_group_id = data.get('labor_group_id') or None
        if labor_group_id:
            try:
                eq.labor_group = Labor.objects.get(id=labor_group_id)
            except Labor.DoesNotExist:
                eq.labor_group = None
        else:
            eq.labor_group = None
    if 'equip_type' in data:
        equip_type = (data.get('equip_type') or 'standard').lower()
        eq.equipment_type = 'Delay' if equip_type == 'delay' else 'Standard'

    eq.save()

    return JsonResponse({})


@csrf_exempt
@require_http_methods(['DELETE'])
def model_equipment_delete(request, model_id, equip_id):
    get_object_or_404(RMCMModel, id=model_id)
    try:
        eq = EquipmentGroup.objects.get(id=equip_id)
    except EquipmentGroup.DoesNotExist:
        return JsonResponse({}, status=204)

    from django.utils import timezone

    eq.deleted_at = timezone.now()
    eq.save()

    return JsonResponse({}, status=204)
