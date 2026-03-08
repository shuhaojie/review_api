from django.db import models
from django.contrib.auth import get_user_model
from api.app.base.models import BaseModel
from api.app.project.models import Project
User = get_user_model()


class Doc(BaseModel):
    CHOICES = (
        (0, "排队中"),
        (1, "审核中"),
        (2, "审核成功"),
        (3, "审核失败"),
    )
    file_name = models.CharField(max_length=255, verbose_name='文件名称')
    file_uuid = models.CharField(max_length=255, verbose_name='文件uuid', unique=True)
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              verbose_name='创建人',
                              null=True,
                              related_name='doc')
    # 这里命名的时候，如果用project_id，django生成的字段名就是project_id_id
    project_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name='项目id',
        related_name='doc'
    )
    status = models.IntegerField(choices=CHOICES,
                                 db_comment="0-排队中, 1-审核中, 2-审核成功, 3-审核失败",
                                 default=0,
                                 help_text="0-排队中, 1-审核中, 2-审核成功, 3-审核失败"  # 添加这行
    )

    class Meta:
        db_table = "doc"
        indexes = [
            models.Index(fields=["project_id", "is_deleted"]),
        ]


class DocStatus(BaseModel):
    CHOICES = (
        (0, "等待"),
        (1, "成功"),
        (2, "失败"),
    )
    doc = models.OneToOneField(Doc, on_delete=models.CASCADE, related_name='doc_status')

    parse_status = models.IntegerField(default=0, choices=CHOICES, db_comment='状态: 0-等待, 1-成功, 2-失败')
    parse_start = models.DateTimeField(null=True, db_comment='解析开始时间')
    parse_end = models.DateTimeField(null=True, db_comment='解析完成时间')

    text_review_status = models.IntegerField(default=0, choices=CHOICES, db_comment='状态: 0-等待, 1-成功, 2-失败')
    text_review_start = models.DateTimeField(null=True, db_comment='文字纠错开始时间')
    text_review_end = models.DateTimeField(null=True, db_comment='文字纠错结束时间')

    financial_review_status = models.IntegerField(default=0, choices=CHOICES, db_comment='状态: 0-等待, 1-成功, 2-失败')
    financial_review_start = models.DateTimeField(null=True, db_comment='财务审核开始时间')
    financial_review_end = models.DateTimeField(null=True, db_comment='财务审核完成时间')

    class Meta:
        db_table = "doc_status"
