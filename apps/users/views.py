from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
import json
from django.contrib.auth import login, logout
from .models import create_user_account, authenticate_user, get_profile_payload


@ensure_csrf_cookie
@require_http_methods(["GET"])
def csrf_cookie(request):
    """Return 200 so the client receives the CSRF cookie (for X-CSRFToken header)."""
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def signup(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email") or ""
    password = data.get("password") or ""
    password_confirm = data.get("password_confirm") or ""
    name = data.get("name") or ""

    user, error = create_user_account(
        name=name,
        email=email,
        password=password,
        password_confirm=password_confirm,
    )
    if error:
        return JsonResponse({"error": error}, status=400)
    return JsonResponse({"message": "Account created"})


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email") or ""
    password = data.get("password") or ""

    user, error = authenticate_user(email=email, password=password)
    if error:
        # Use 401 for auth errors, 400 for validation; model currently returns generic string.
        status_code = 401 if error == "Invalid credentials" else 400
        return JsonResponse({"error": error}, status=status_code)

    login(request, user)

    return JsonResponse({"message": "Login successful"})


@require_http_methods(["GET"])
def profile(request):
    # if not request.user.is_authenticated:
    #     return JsonResponse({"error": "Unauthorized"}, status=401)

    return JsonResponse(get_profile_payload(request.user))


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)

    response = JsonResponse({"message": "Logged out"})
    # Explicitly clear session and CSRF cookies on the client.
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    response.delete_cookie("csrftoken")
    return response
