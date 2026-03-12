from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from organizations.models import Organization


class UserProfile(models.Model):
    """
    Extra per-user data for the RMCT app.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="users"
    )

    full_name = models.CharField(max_length=255)

    role = models.CharField(max_length=50, db_index=True, default="user")

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:

        db_table = "user_profiles"

        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()

def create_user_account(*, name: str, email: str, password: str, password_confirm: str, organization):

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

    UserProfile.objects.create(
        user=user,
        full_name=name,
        organization=organization
    )

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

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"full_name": user.get_full_name() or user.email},
    )

    name = profile.full_name or user.get_full_name() or user.email

    return {
        "email": user.email,
        "name": name,
        "organization_id": profile.organization_id,
        "role": profile.role,
    }