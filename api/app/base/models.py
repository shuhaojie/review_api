from django.db import models


class BaseModel(models.Model):
    """全局抽象基类：自动记录创建/更新时间"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_deleted = models.BooleanField('是否删除', default=False)

    class Meta:
        abstract = True          # 关键：不会在数据库生成表
        ordering = ['-create_time']