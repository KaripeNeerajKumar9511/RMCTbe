from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class UserProfile(models.Model):
    """
    Extra per-user data for the RMCT app.

    Credentials (username/email + hashed password) are stored in Django's
    built-in auth User model; this model is for any additional fields you
    want to associate with each user.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()


def create_user_account(*, name: str, email: str, password: str, password_confirm: str):
    """
    Encapsulate all DB interactions for signup.

    Returns (user, error_message). If error_message is not None, user will be None.
    """
    email = (email or "").strip()
    name = (name or "").strip()

    if not email:
        return None, "Email is required"
    if not name:
        return None, "Name is required"
    if not password:
        return None, "Password is required"
    if password != password_confirm:
        return None, "Passwords do not match"
    if User.objects.filter(email=email).exists():
        return None, "An account with this email already exists"

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name,
    )
    UserProfile.objects.create(user=user, full_name=name)
    return user, None


def authenticate_user(*, email: str, password: str):
    """
    All auth + DB checks for login.

    Returns (user, error_message). If error_message is not None, user will be None.
    """
    email = (email or "").strip()
    password = password or ""

    if not email or not password:
        return None, "Email and password are required"

    user = authenticate(username=email, password=password)
    if user is None:
        return None, "Invalid credentials"

    return user, None


def get_profile_payload(user: User):
    """
    Central place to build the profile JSON sent to the client.
    """
    # Ensure we always have a profile row
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"full_name": user.get_full_name() or user.email},
    )
    name = profile.full_name or user.get_full_name() or user.email
    return {
        "email": user.email,
        "name": name,
    }
