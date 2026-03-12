import uuid
from django.db import models
from apps.organizations.models import Organization


class Labor(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="labors"
    )

    name = models.CharField(max_length=255)

    count = models.IntegerField(default=1)

    overtime_percent = models.FloatField(default=0)

    unavailability_percent = models.FloatField(default=0)

    department = models.CharField(max_length=255, null=True, blank=True)

    setup_factor = models.FloatField(default=1)

    run_factor = models.FloatField(default=1)

    variable_factor = models.FloatField(default=1)

    prioritize = models.BooleanField(default=False, db_index=True)

    lab1 = models.FloatField(null=True, blank=True)
    lab2 = models.FloatField(null=True, blank=True)
    lab3 = models.FloatField(null=True, blank=True)
    lab4 = models.FloatField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:

        db_table = "labors"

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_labor_name_per_org"
            )
        ]

        indexes = [
            models.Index(fields=["organization", "department"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return self.name