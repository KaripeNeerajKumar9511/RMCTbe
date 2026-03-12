import uuid
from django.db import models


class Organization(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255, db_index=True)

    organization_code = models.CharField(max_length=50, unique=True)

    slug = models.SlugField(unique=True)

    plan_type = models.CharField(max_length=50, null=True, blank=True)

    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)

    country = models.CharField(max_length=100, null=True, blank=True)
    timezone = models.CharField(max_length=100, null=True, blank=True)

    status = models.SmallIntegerField(default=1, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "organizations"

        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]