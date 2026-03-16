import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Organization


def _parse_json(request):
    try:
        return json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return {}


# CREATE ORGANIZATION
@csrf_exempt
@require_http_methods(["POST"])
def create_organization(request):
    data = _parse_json(request)

    org = Organization.objects.create(
        name=data.get("name"),
        organization_code=data.get("organization_code"),
        slug=data.get("slug"),
        plan_type=data.get("plan_type"),
        contact_email=data.get("contact_email"),
        contact_phone=data.get("contact_phone"),
        country=data.get("country"),
        timezone=data.get("timezone"),
        status=data.get("status", 1)
    )

    return JsonResponse({
        "message": "Organization created successfully",
        "id": str(org.id)
    }, status=201)


# LIST ALL ORGANIZATIONS
@require_http_methods(["GET"])
def list_organizations(request):

    orgs = Organization.objects.filter(deleted_at__isnull=True).values()

    data = list(orgs)

    return JsonResponse(data, safe=False)


# GET SINGLE ORGANIZATION
@require_http_methods(["GET"])
def get_organization(request, org_id):

    org = get_object_or_404(Organization, id=org_id, deleted_at__isnull=True)

    data = {
        "id": str(org.id),
        "name": org.name,
        "organization_code": org.organization_code,
        "slug": org.slug,
        "plan_type": org.plan_type,
        "contact_email": org.contact_email,
        "contact_phone": org.contact_phone,
        "country": org.country,
        "timezone": org.timezone,
        "status": org.status,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
    }

    return JsonResponse(data)


# UPDATE ORGANIZATION
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_organization(request, org_id):

    org = get_object_or_404(Organization, id=org_id, deleted_at__isnull=True)

    data = _parse_json(request)

    org.name = data.get("name", org.name)
    org.organization_code = data.get("organization_code", org.organization_code)
    org.slug = data.get("slug", org.slug)
    org.plan_type = data.get("plan_type", org.plan_type)
    org.contact_email = data.get("contact_email", org.contact_email)
    org.contact_phone = data.get("contact_phone", org.contact_phone)
    org.country = data.get("country", org.country)
    org.timezone = data.get("timezone", org.timezone)
    org.status = data.get("status", org.status)

    org.save()

    return JsonResponse({
        "message": "Organization updated successfully"
    })


# DELETE ORGANIZATION (SOFT DELETE)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_organization(request, org_id):

    org = get_object_or_404(Organization, id=org_id, deleted_at__isnull=True)

    from django.utils import timezone
    org.deleted_at = timezone.now()
    org.save()

    return JsonResponse({
        "message": "Organization deleted successfully"
    })