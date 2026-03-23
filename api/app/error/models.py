from api.app.base.models import BaseModel
from django.db import models
from api.app.doc.models import Doc


class TextError(BaseModel):
    origin_text = models.CharField(max_length=255, db_comment="Original text", null=False)
    correct_text = models.CharField(max_length=255, db_comment="Suggested correction", null=False)
    pos_list = models.JSONField(db_comment="Position list", null=False, default=list)
    page_id = models.IntegerField(db_comment="Page number", null=False)
    cross_page = models.BooleanField(db_comment="Spans multiple pages", null=False, default=False)
    doc_id = models.ForeignKey(
        Doc,
        on_delete=models.CASCADE,
        verbose_name='Document',
        related_name='doc_text_error'
    )

    class Meta:
        db_table = "text_error"


class FinancialError(BaseModel):
    origin_text = models.CharField(max_length=255, db_comment="Original text", null=False, verbose_name='Value in table')
    correct_text = models.CharField(max_length=255, db_comment="Suggested correction", null=False, verbose_name='Computed value')
    pos_list = models.JSONField(db_comment="Position list", null=False, default=list)  # Use default=list, not default=[]
    type = models.CharField(
        max_length=50,
        db_comment="Error type",
        null=False,
        default='formula',
        verbose_name="Error type: accounting_formula=formula relationship error, accounting_consistency=data entry error"
    )
    page_id = models.IntegerField(db_comment="Page number", null=False, default=0)
    cross_page = models.BooleanField(db_comment="Spans multiple pages", null=False, default=False)
    formula = models.TextField(default='', verbose_name='Formula expression')
    formula_value = models.TextField(default='', verbose_name='Formula with substituted values')
    formula_result_name = models.TextField(default='', verbose_name='Financial account for the formula result')
    formula_breakdown = models.JSONField(db_comment="Formula breakdown for frontend use", null=False, default=list, verbose_name='Formula breakdown for frontend use')
    table_title = models.CharField(max_length=255, db_comment="Table name in document", null=False, default='', verbose_name='Table name in document')
    report_period = models.CharField(max_length=255, db_comment="Reporting period", null=False, default='', verbose_name='Reporting period')

    CHOICES = (
        (0, "Error"),
        (1, "Suspected Error"),
        (2, "Correct"),
    )
    status = models.IntegerField(choices=CHOICES,
                                 db_comment="0=Error, 1=Suspected Error, 2=Correct",
                                 default=0,
                                 help_text="0=Error, 1=Suspected Error, 2=Correct")
    doc_id = models.ForeignKey(
        Doc,
        on_delete=models.CASCADE,
        verbose_name='Document',
        related_name='doc_financial_error'
    )

    class Meta:
        db_table = "financial_error"
