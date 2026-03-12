import uuid
from django.db import models
from apps.organizations.models import Organization


class Product(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="products"
    )

    name = models.CharField(max_length=255)

    end_demand = models.IntegerField(default=0)

    lot_size = models.IntegerField(default=1)

    transfer_batch = models.IntegerField(default=-1)

    department_area = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    demand_factor = models.FloatField(default=1)

    lot_factor = models.FloatField(default=1)

    variability_factor = models.FloatField(default=1)

    make_to_stock = models.BooleanField(default=False)

    gather_transfer_batches = models.BooleanField(default=False)

    prod1 = models.FloatField(default=0)
    prod2 = models.FloatField(default=0)
    prod3 = models.FloatField(default=0)
    prod4 = models.FloatField(default=0)

    comments = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:

        db_table = "products"

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_product_per_org"
            )
        ]

        indexes = [
            models.Index(fields=["organization", "department_area"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return self.name