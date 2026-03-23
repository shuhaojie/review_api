from django.db import models
from django.contrib.auth import get_user_model
from api.app.base.models import BaseModel
from api.app.project.models import Project
User = get_user_model()


class Doc(BaseModel):
    CHOICES = (
        (0, "Queued"),
        (1, "Reviewing"),
        (2, "Review Succeeded"),
        (3, "Review Failed"),
    )
    file_name = models.CharField(max_length=255, verbose_name='File Name')
    file_uuid = models.CharField(max_length=255, verbose_name='File UUID', unique=True)
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              verbose_name='Owner',
                              null=True,
                              related_name='doc')
    # Named 'project_id' intentionally; using this name causes Django to generate 'project_id_id' as the column name
    project_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name='Project',
        related_name='doc'
    )
    status = models.IntegerField(choices=CHOICES,
                                 db_comment="0=Queued, 1=Reviewing, 2=Succeeded, 3=Failed",
                                 default=0,
                                 help_text="0=Queued, 1=Reviewing, 2=Succeeded, 3=Failed"
    )

    class Meta:
        db_table = "doc"
        indexes = [
            models.Index(fields=["project_id", "is_deleted"]),
        ]


class DocStatus(BaseModel):
    CHOICES = (
        (0, "Pending"),
        (1, "Succeeded"),
        (2, "Failed"),
    )
    doc = models.OneToOneField(Doc, on_delete=models.CASCADE, related_name='doc_status')

    parse_status = models.IntegerField(default=0, choices=CHOICES, db_comment='Status: 0=Pending, 1=Succeeded, 2=Failed')
    parse_start = models.DateTimeField(null=True, db_comment='Parse start time')
    parse_end = models.DateTimeField(null=True, db_comment='Parse end time')

    text_review_status = models.IntegerField(default=0, choices=CHOICES, db_comment='Status: 0=Pending, 1=Succeeded, 2=Failed')
    text_review_start = models.DateTimeField(null=True, db_comment='Text review start time')
    text_review_end = models.DateTimeField(null=True, db_comment='Text review end time')

    financial_review_status = models.IntegerField(default=0, choices=CHOICES, db_comment='Status: 0=Pending, 1=Succeeded, 2=Failed')
    financial_review_start = models.DateTimeField(null=True, db_comment='Financial review start time')
    financial_review_end = models.DateTimeField(null=True, db_comment='Financial review end time')

    class Meta:
        db_table = "doc_status"
