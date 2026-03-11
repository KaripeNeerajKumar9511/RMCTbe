"""
RMCT REST API: models, versions, scenarios, changes, results.
Matches frontend contract in docs/BACKEND_API.md. No Supabase; all data in Django DB.
"""
import json
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import get_object_or_404

from .models import RMCMModel, ModelVersion, Scenario, ScenarioChange, ScenarioResult


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return None


def _model_to_payload(m: RMCMModel) -> dict:
    """Serialize RMCMModel to frontend Model shape."""
    return {
        'id': str(m.id),
        'name': m.name,
        'description': m.description or '',
        'tags': m.tags or [],
        'created_at': m.created_at.isoformat() if m.created_at else '',
        'updated_at': m.updated_at.isoformat() if m.updated_at else '',
        'last_run_at': m.last_run_at.isoformat() if m.last_run_at else None,
        'run_status': m.run_status or 'never_run',
        'is_archived': bool(m.is_archived),
        'is_demo': bool(m.is_demo),
        'is_starred': bool(m.is_starred),
        'general': m.general or {},
        'param_names': m.param_names or {},
        'labor': m.labor or [],
        'equipment': m.equipment or [],
        'products': m.products or [],
        'operations': m.operations or [],
        'routing': m.routing or [],
        'ibom': m.ibom or [],
    }


# ─── Models ─────────────────────────────────────────────────────────────

def model_list_or_create(request):
    """GET /api/models — list all. POST /api/models — create (body has full model with id)."""
    if request.method == 'GET':
        qs = RMCMModel.objects.all()
        if request.user.is_authenticated:
            qs = qs.filter(owner=request.user)
        payload = [_model_to_payload(m) for m in qs]
        return JsonResponse(payload, safe=False)
    if request.method == 'POST':
        return model_save(request, model_id=None)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_http_methods(['GET'])
def model_list(request):
    """GET /api/models — list all models."""
    qs = RMCMModel.objects.all()
    if request.user.is_authenticated:
        qs = qs.filter(owner=request.user)
    payload = [_model_to_payload(m) for m in qs]
    return JsonResponse(payload, safe=False)


@require_http_methods(['GET'])
def model_detail(request, model_id):
    """GET /api/models/:id — get one model."""
    m = RMCMModel.objects.filter(id=model_id).first()
    if not m:
        return JsonResponse(None, safe=False)
    return JsonResponse(_model_to_payload(m))


@require_http_methods(['POST', 'PUT'])
def model_save(request, model_id=None):
    """
    POST /api/models — create (body includes id) or PUT /api/models/:id — update full model.
    """
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    model_id = model_id or data.get('id')
    if not model_id:
        return JsonResponse({'error': 'id required'}, status=400)
    try:
        uid = uuid.UUID(str(model_id))
    except ValueError:
        return JsonResponse({'error': 'Invalid id'}, status=400)
    from django.utils import timezone
    updated_at = timezone.now()
    defaults = {
        'name': data.get('name', ''),
        'description': data.get('description', ''),
        'tags': data.get('tags', []),
        'last_run_at': data.get('last_run_at'),
        'run_status': data.get('run_status', 'never_run'),
        'is_archived': data.get('is_archived', False),
        'is_demo': data.get('is_demo', False),
        'is_starred': data.get('is_starred', False),
        'general': data.get('general', {}),
        'param_names': data.get('param_names', {}),
        'labor': data.get('labor', []),
        'equipment': data.get('equipment', []),
        'products': data.get('products', []),
        'operations': data.get('operations', []),
        'routing': data.get('routing', []),
        'ibom': data.get('ibom', []),
    }
    if request.user.is_authenticated:
        defaults['owner'] = request.user
    obj, created = RMCMModel.objects.update_or_create(id=uid, defaults=defaults)
    return JsonResponse(_model_to_payload(obj), status=201 if created else 200)


@require_http_methods(['PATCH'])
def model_patch(request, model_id):
    """PATCH /api/models/:id — partial update (metadata or nested)."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    for key in ('name', 'description', 'tags', 'run_status', 'last_run_at', 'is_archived', 'is_demo', 'is_starred',
                'general', 'param_names', 'labor', 'equipment', 'products', 'operations', 'routing', 'ibom'):
        if key in data:
            setattr(m, key, data[key])
    m.save()
    return JsonResponse(_model_to_payload(m))


@require_http_methods(['DELETE'])
def model_delete(request, model_id):
    """DELETE /api/models/:id."""
    m = RMCMModel.objects.filter(id=model_id).first()
    if m:
        m.delete()
    return JsonResponse({}, status=204)


# ─── Param names ────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def model_param_names(request, model_id):
    """GET /api/models/:id/param-names."""
    m = RMCMModel.objects.filter(id=model_id).values_list('param_names', flat=True).first()
    if m is None:
        return JsonResponse(None, safe=False)
    return JsonResponse(m or {})


@require_http_methods(['PUT'])
def model_param_names_upsert(request, model_id):
    """PUT /api/models/:id/param-names — merge param names."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    pn = dict(m.param_names or {})
    pn.update(data)
    m.param_names = pn
    m.save()
    return JsonResponse({})


# ─── General ─────────────────────────────────────────────────────────────

@require_http_methods(['PATCH'])
def model_general(request, model_id):
    """PATCH /api/models/:id/general."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    g = dict(m.general or {})
    g.update(data)
    m.general = g
    m.save()
    return JsonResponse({})


# ─── Labor ──────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_labor_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    labor = list(m.labor or [])
    labor.append(data)
    m.labor = labor
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PATCH'])
def model_labor_update(request, model_id, labor_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    labor = list(m.labor or [])
    for i, L in enumerate(labor):
        if str(L.get('id')) == str(labor_id):
            labor[i] = {**L, **data}
            m.labor = labor
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'Labor not found'}, status=404)


@require_http_methods(['DELETE'])
def model_labor_delete(request, model_id, labor_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    labor = [L for L in (m.labor or []) if str(L.get('id')) != str(labor_id)]
    m.labor = labor
    m.equipment = [{**e, 'labor_group_id': '' if str(e.get('labor_group_id')) == str(labor_id) else e.get('labor_group_id')} for e in (m.equipment or [])]
    m.save()
    return JsonResponse({}, status=204)


# ─── Equipment ───────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_equipment_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    equipment = list(m.equipment or [])
    equipment.append(data)
    m.equipment = equipment
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PATCH'])
def model_equipment_update(request, model_id, equip_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    equipment = list(m.equipment or [])
    for i, e in enumerate(equipment):
        if str(e.get('id')) == str(equip_id):
            equipment[i] = {**e, **data}
            m.equipment = equipment
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'Equipment not found'}, status=404)


@require_http_methods(['DELETE'])
def model_equipment_delete(request, model_id, equip_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    m.equipment = [e for e in (m.equipment or []) if str(e.get('id')) != str(equip_id)]
    m.operations = [{**o, 'equip_id': '' if str(o.get('equip_id')) == str(equip_id) else o.get('equip_id')} for o in (m.operations or [])]
    m.save()
    return JsonResponse({}, status=204)


# ─── Products ───────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_products_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    products = list(m.products or [])
    products.append(data)
    m.products = products
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PATCH'])
def model_products_update(request, model_id, product_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    products = list(m.products or [])
    for i, p in enumerate(products):
        if str(p.get('id')) == str(product_id):
            products[i] = {**p, **data}
            m.products = products
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'Product not found'}, status=404)


@require_http_methods(['DELETE'])
def model_products_delete(request, model_id, product_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    pid = str(product_id)
    m.products = [p for p in (m.products or []) if str(p.get('id')) != pid]
    m.operations = [o for o in (m.operations or []) if str(o.get('product_id')) != pid]
    m.routing = [r for r in (m.routing or []) if str(r.get('product_id')) != pid]
    m.ibom = [b for b in (m.ibom or []) if str(b.get('parent_product_id')) != pid and str(b.get('component_product_id')) != pid]
    m.save()
    return JsonResponse({}, status=204)


@require_http_methods(['DELETE'])
def model_products_clear_ops_routing(request, model_id, product_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    pid = str(product_id)
    m.operations = [o for o in (m.operations or []) if str(o.get('product_id')) != pid]
    m.routing = [r for r in (m.routing or []) if str(r.get('product_id')) != pid]
    m.run_status = 'needs_recalc'
    m.save()
    return JsonResponse({}, status=204)


# ─── Operations ──────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_operations_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    operations = list(m.operations or [])
    operations.append(data)
    m.operations = operations
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PATCH'])
def model_operations_update(request, model_id, op_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    operations = list(m.operations or [])
    for i, o in enumerate(operations):
        if str(o.get('id')) == str(op_id):
            operations[i] = {**o, **data}
            m.operations = operations
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'Operation not found'}, status=404)


@require_http_methods(['DELETE'])
def model_operations_delete(request, model_id, op_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    op = next((o for o in (m.operations or []) if str(o.get('id')) == str(op_id)), None)
    if not op:
        return JsonResponse({}, status=204)
    product_id = op.get('product_id')
    op_name = op.get('op_name')
    m.operations = [o for o in (m.operations or []) if str(o.get('id')) != str(op_id)]
    m.routing = [r for r in (m.routing or []) if not (str(r.get('product_id')) == str(product_id) and r.get('from_op_name') == op_name)]
    m.save()
    return JsonResponse({}, status=204)


# ─── Routing ─────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_routing_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    routing = list(m.routing or [])
    routing.append(data)
    m.routing = routing
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PUT'])
def model_routing_set(request, model_id):
    """PUT /api/models/:id/routing — replace routing for a product (body: productId, entries)."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    product_id = data.get('productId') or data.get('product_id')
    entries = data.get('entries', [])
    if product_id is None:
        return JsonResponse({'error': 'productId required'}, status=400)
    pid = str(product_id)
    m.routing = [r for r in (m.routing or []) if str(r.get('product_id')) != pid] + entries
    m.save()
    return JsonResponse({})


@require_http_methods(['PATCH'])
def model_routing_update(request, model_id, route_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    routing = list(m.routing or [])
    for i, r in enumerate(routing):
        if str(r.get('id')) == str(route_id):
            routing[i] = {**r, **data}
            m.routing = routing
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'Routing not found'}, status=404)


@require_http_methods(['DELETE'])
def model_routing_delete(request, model_id, route_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    m.routing = [r for r in (m.routing or []) if str(r.get('id')) != str(route_id)]
    m.save()
    return JsonResponse({}, status=204)


# ─── IBOM ───────────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def model_ibom_create(request, model_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    ibom = list(m.ibom or [])
    ibom.append(data)
    m.ibom = ibom
    m.save()
    return JsonResponse({}, status=201)


@require_http_methods(['PUT'])
def model_ibom_set_for_parent(request, model_id, parent_id):
    """PUT /api/models/:id/ibom/:parentId — set all IBOM entries for a parent product."""
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    entries = data if isinstance(data, list) else data.get('entries', [])
    pid = str(parent_id)
    m.ibom = [b for b in (m.ibom or []) if str(b.get('parent_product_id')) != pid] + entries
    m.save()
    return JsonResponse({})


@require_http_methods(['PATCH'])
def model_ibom_update(request, model_id, entry_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    ibom = list(m.ibom or [])
    for i, b in enumerate(ibom):
        if str(b.get('id')) == str(entry_id):
            ibom[i] = {**b, **data}
            m.ibom = ibom
            m.save()
            return JsonResponse({})
    return JsonResponse({'error': 'IBOM entry not found'}, status=404)


@require_http_methods(['DELETE'])
def model_ibom_delete(request, model_id, entry_id):
    m = get_object_or_404(RMCMModel, id=model_id)
    m.ibom = [b for b in (m.ibom or []) if str(b.get('id')) != str(entry_id)]
    m.save()
    return JsonResponse({}, status=204)


# ─── Versions ────────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def version_list(request, model_id):
    """GET /api/models/:modelId/versions."""
    qs = ModelVersion.objects.filter(model_id=model_id).order_by('-created_at')
    payload = [{'id': str(v.id), 'label': v.label, 'created_at': v.created_at.isoformat()} for v in qs]
    return JsonResponse(payload, safe=False)


@require_http_methods(['POST'])
def version_create(request, model_id):
    """POST /api/models/:modelId/versions — body: { label, snapshot }."""
    get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    label = data.get('label', '')
    snapshot = data.get('snapshot', {})
    vid = uuid.uuid4()
    ModelVersion.objects.create(id=vid, model_id=model_id, label=label, snapshot=snapshot)
    return JsonResponse({'id': str(vid)}, status=201)


@require_http_methods(['GET'])
def version_snapshot(request, version_id):
    """GET /api/versions/:versionId — snapshot + created_at."""
    v = get_object_or_404(ModelVersion, id=version_id)
    return JsonResponse({'snapshot': v.snapshot, 'created_at': v.created_at.isoformat()})


@require_http_methods(['PATCH'])
def version_patch(request, version_id):
    """PATCH /api/versions/:versionId — update label."""
    v = get_object_or_404(ModelVersion, id=version_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    if 'label' in data:
        v.label = data['label']
        v.save()
    return JsonResponse({})


@require_http_methods(['DELETE'])
def version_delete(request, version_id):
    v = ModelVersion.objects.filter(id=version_id).first()
    if v:
        v.delete()
    return JsonResponse({}, status=204)


@require_http_methods(['POST'])
def version_restore(request, model_id, version_id):
    """POST /api/models/:modelId/versions/:versionId/restore — apply snapshot to model, return Model."""
    m = get_object_or_404(RMCMModel, id=model_id)
    v = ModelVersion.objects.filter(id=version_id, model_id=model_id).first()
    if not v:
        return JsonResponse({'error': 'Version not found'}, status=404)
    snap = v.snapshot or {}
    m.general = snap.get('general', m.general)
    m.labor = snap.get('labor', m.labor)
    m.equipment = snap.get('equipment', m.equipment)
    m.products = snap.get('products', m.products)
    m.operations = snap.get('operations', m.operations)
    m.routing = snap.get('routing', m.routing)
    m.ibom = snap.get('ibom', m.ibom)
    if snap.get('param_names'):
        m.param_names = snap['param_names']
    m.run_status = 'needs_recalc'
    m.save()
    return JsonResponse(_model_to_payload(m))


# ─── Scenarios ───────────────────────────────────────────────────────────

def _scenario_to_payload(s: Scenario, changes_list: list) -> dict:
    return {
        'id': str(s.id),
        'modelId': str(s.model_id),
        'name': s.name,
        'description': s.description or '',
        'familyId': str(s.family_id) if s.family_id else None,
        'status': s.status or 'needs_recalc',
        'changes': changes_list,
        'createdAt': s.created_at.isoformat(),
        'updatedAt': s.updated_at.isoformat(),
    }


def scenario_list_or_create(request, model_id):
    """GET /api/models/:modelId/scenarios — list. POST — create (body: name, description)."""
    if request.method == 'POST':
        return scenario_create(request, model_id)
    return scenario_list(request, model_id)


@require_http_methods(['GET'])
def scenario_list(request, model_id):
    """GET /api/models/:modelId/scenarios — scenarios + changes + results."""
    m = get_object_or_404(RMCMModel, id=model_id)
    scenarios_qs = Scenario.objects.filter(model=m, is_basecase=False).order_by('-updated_at')
    scenario_ids = [s.id for s in scenarios_qs]
    changes_qs = ScenarioChange.objects.filter(scenario_id__in=scenario_ids)
    changes_by_scenario = {}
    for c in changes_qs:
        key = str(c.scenario_id)
        if key not in changes_by_scenario:
            changes_by_scenario[key] = []
        changes_by_scenario[key].append({
            'id': str(c.id),
            'dataType': c.data_type,
            'entityId': c.entity_id or '',
            'entityName': c.entity_name or '',
            'field': c.field_name,
            'fieldLabel': c.field_name,
            'basecaseValue': c.basecase_value,
            'whatIfValue': c.whatif_value,
        })
    results_map = {}
    for s in scenarios_qs:
        try:
            r = s.result
            results_map[str(s.id)] = r.results
        except ScenarioResult.DoesNotExist:
            pass
    scenarios_payload = []
    for s in scenarios_qs:
        scenarios_payload.append(_scenario_to_payload(s, changes_by_scenario.get(str(s.id), [])))
    return JsonResponse({'scenarios': scenarios_payload, 'results': results_map})


def scenario_basecase_results(request, model_id):
    """GET /api/models/:modelId/scenarios/basecase/results — return results. PUT — save results."""
    if request.method == 'GET':
        base = Scenario.objects.filter(model_id=model_id, is_basecase=True).first()
        if not base:
            return JsonResponse(None, safe=False)
        try:
            r = base.result
            return JsonResponse(r.results)
        except ScenarioResult.DoesNotExist:
            return JsonResponse(None, safe=False)
    if request.method == 'PUT':
        return scenario_basecase_save_results(request, model_id)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_http_methods(['POST'])
def scenario_ensure_basecase(request, model_id):
    """POST /api/models/:modelId/scenarios/basecase — idempotent, return { id }."""
    get_object_or_404(RMCMModel, id=model_id)
    base = Scenario.objects.filter(model_id=model_id, is_basecase=True).first()
    if base:
        return JsonResponse({'id': str(base.id)})
    sid = uuid.uuid4()
    Scenario.objects.create(id=sid, model_id=model_id, name='Basecase', description='', is_basecase=True, status='needs_recalc')
    return JsonResponse({'id': str(sid)}, status=201)


@require_http_methods(['POST'])
def scenario_create(request, model_id):
    """POST /api/models/:modelId/scenarios — body: { name, description }."""
    get_object_or_404(RMCMModel, id=model_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    name = data.get('name', '')
    description = data.get('description', '')
    sid = uuid.uuid4()
    Scenario.objects.create(id=sid, model_id=model_id, name=name, description=description, is_basecase=False, status='needs_recalc')
    return JsonResponse({'id': str(sid)}, status=201)


@require_http_methods(['PATCH'])
def scenario_patch(request, scenario_id):
    """PATCH /api/scenarios/:id — name, description, status."""
    s = get_object_or_404(Scenario, id=scenario_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    for key in ('name', 'description', 'status'):
        if key in data:
            setattr(s, key, data[key])
    s.save()
    return JsonResponse({})


@require_http_methods(['DELETE'])
def scenario_delete(request, scenario_id):
    s = Scenario.objects.filter(id=scenario_id).first()
    if s:
        s.delete()
    return JsonResponse({}, status=204)


@require_http_methods(['PUT'])
def scenario_upsert_change(request, scenario_id):
    """PUT /api/scenarios/:id/changes — body: ScenarioChange."""
    s = get_object_or_404(Scenario, id=scenario_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    change_id = data.get('id')
    if not change_id:
        change_id = uuid.uuid4()
    else:
        try:
            change_id = uuid.UUID(str(change_id))
        except (ValueError, TypeError):
            change_id = uuid.uuid4()
    entity_id = data.get('entityId') or data.get('entity_id', '')
    entity_name = data.get('entityName') or data.get('entity_name', '')
    field = data.get('field') or data.get('field_name', '')
    basecase_value = str(data.get('basecaseValue', data.get('basecase_value', '')))
    whatif_value = str(data.get('whatIfValue', data.get('whatif_value', '')))
    data_type = data.get('dataType') or data.get('data_type', '')
    defaults = {
        'scenario': s,
        'data_type': data_type,
        'entity_id': entity_id,
        'entity_name': entity_name,
        'field_name': field,
        'basecase_value': basecase_value,
        'whatif_value': whatif_value,
    }
    ScenarioChange.objects.update_or_create(id=change_id, defaults=defaults)
    return JsonResponse({})


@require_http_methods(['DELETE'])
def scenario_remove_change(request, scenario_id, change_id):
    ScenarioChange.objects.filter(scenario_id=scenario_id, id=change_id).delete()
    return JsonResponse({}, status=204)


@require_http_methods(['PUT'])
def scenario_save_results(request, scenario_id):
    """PUT /api/scenarios/:id/results — body: CalcResults."""
    s = get_object_or_404(Scenario, id=scenario_id)
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    ScenarioResult.objects.update_or_create(scenario=s, defaults={'results': data})
    return JsonResponse({})


@require_http_methods(['PUT'])
def scenario_basecase_save_results(request, model_id):
    """PUT /api/models/:modelId/scenarios/basecase/results — body: CalcResults."""
    base = Scenario.objects.filter(model_id=model_id, is_basecase=True).first()
    if not base:
        base = Scenario.objects.create(id=uuid.uuid4(), model_id=model_id, name='Basecase', description='', is_basecase=True, status='calculated')
    data = _parse_json(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    ScenarioResult.objects.update_or_create(scenario=base, defaults={'results': data})
    return JsonResponse({})


# ─── Seed demo ───────────────────────────────────────────────────────────

@require_http_methods(['POST'])
def seed_demo(request):
    """POST /api/models/seed-demo — create demo model from frontend createDemoModel() payload if needed."""
    from django.utils import timezone
    data = _parse_json(request)
    if data is None:
        data = {}
    # If client sends full demo model, use it; else we could generate server-side
    model_id = data.get('id')
    if not model_id:
        model_id = uuid.uuid4()
    name = data.get('name', 'Hub Manufacturing Cell — Demo')
    RMCMModel.objects.get_or_create(
        id=model_id,
        defaults={
            'name': name,
            'description': data.get('description', ''),
            'tags': data.get('tags', ['Demo', 'Tutorial']),
            'run_status': 'never_run',
            'is_demo': True,
            'general': data.get('general', {}),
            'param_names': data.get('param_names', {}),
            'labor': data.get('labor', []),
            'equipment': data.get('equipment', []),
            'products': data.get('products', []),
            'operations': data.get('operations', []),
            'routing': data.get('routing', []),
            'ibom': data.get('ibom', []),
            'owner': request.user if request.user.is_authenticated else None,
        },
    )
    return JsonResponse({'id': str(model_id)}, status=201)
