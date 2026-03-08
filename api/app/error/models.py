from api.app.base.models import BaseModel
from django.db import models
from api.app.doc.models import Doc


class TextError(BaseModel):
    origin_text = models.CharField(max_length=255, db_comment="原文", null=False)
    correct_text = models.CharField(max_length=255, db_comment="修改建议", null=False)
    pos_list = models.JSONField(db_comment="位置列表", null=False, default=list)
    page_id = models.IntegerField(db_comment="所在页码数", null=False)
    cross_page = models.BooleanField(db_comment="是否跨页", null=False, default=False)
    doc_id = models.ForeignKey(
        Doc,
        on_delete=models.CASCADE,
        verbose_name='项目id',
        related_name='doc_text_error'
    )

    class Meta:
        db_table = "text_error"


class FinancialError(BaseModel):
    origin_text = models.CharField(max_length=255, db_comment="原文", null=False, verbose_name='文件表格中的结果')
    correct_text = models.CharField(max_length=255, db_comment="修改建议", null=False, verbose_name='公式计算的结果')
    pos_list = models.JSONField(db_comment="位置列表", null=False, default=list)  # 注意使用list而不是[]
    type = models.CharField(max_length=50, db_comment="类型", null=False,default='formula',verbose_name="错误类型；<br/>accounting_formula-财务审核错误（勾稽关系错误）<br/>accounting_consistency-财务审核错误（数据填报错误）")
    page_id = models.IntegerField(db_comment="所在页码数", null=False, default=0)
    cross_page = models.BooleanField(db_comment="是否跨页", null=False, default=False)
    formula = models.TextField(default='',verbose_name='计算公式')
    formula_value = models.TextField(default='',verbose_name='带入数值后计算公式')
    formula_result_name = models.TextField(default='',verbose_name='计算结果对应的财务科目')
    formula_breakdown = models.JSONField(db_comment="公式拆解,供前端使用", null=False, default=list,verbose_name='公式拆解,供前端使用')
    table_title = models.CharField(max_length=255, db_comment="文件中的表名", null=False, default='', verbose_name='文件中的表名')
    report_period = models.CharField(max_length=255, db_comment="报告期", null=False, default='', verbose_name='报告期')
    
    CHOICES = (
        (0, "错误"),
        (1, "疑似错误"),
        (2, "正确"),
    )
    status = models.IntegerField(choices=CHOICES,
                                 db_comment="0-错误, 1-疑似错误, 2-正确",
                                 default=0,
                                 help_text="0-错误, 1-疑似错误, 2-正确")  # 添加这行
    doc_id = models.ForeignKey(
        Doc,
        on_delete=models.CASCADE,
        verbose_name='项目id',
        related_name='doc_financial_error'
    )

    class Meta:
        db_table = "financial_error"
