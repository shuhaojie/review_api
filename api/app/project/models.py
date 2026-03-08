from django.db import models
from api.app.base.models import BaseModel
from api.app.user.models import User


class Project(BaseModel):
    CHOICES = (
        (0, "Private project"),
        (1, "Public project"),
    )
    name = models.CharField(max_length=255, verbose_name='Project name', db_comment='Project name')
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,  # Set to null after deletion
                              null=True,
                              blank=True,
                              related_name='owner_user',  # For reverse query
                              verbose_name='Creator')
    viewers = models.ManyToManyField(User,
                                     related_name='viewer_users',
                                     verbose_name="Visible users",
                                     blank=True,
                                     help_text='Users who can view this project')
    project_type = models.IntegerField(choices=CHOICES, default=1, db_comment="0-Private project, 1-Public project")

    class Meta:
        db_table = "project"

    def __str__(self):
        return self.name
