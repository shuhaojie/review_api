from django.db import models


class BaseModel(models.Model):
    """Abstract base model that tracks creation/update timestamps and soft deletion."""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    update_time = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    is_deleted = models.BooleanField('Is Deleted', default=False)

    class Meta:
        abstract = True  # Does not create a database table
        ordering = ['-create_time']
