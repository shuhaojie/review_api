from django.db import models
from api.app.base.models import BaseModel
from api.app.user.models import User


class Prompt(BaseModel):
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name='Creator',
        null=True,
        db_column='creator_id',  # Database column name is still creator_id
        related_name='promote'
    )
    name = models.CharField(max_length=100, unique=False)
    content = models.TextField()
    is_active = models.BooleanField("Is active", default=False)

    class Meta:
        db_table = 'llm_prompt'
        ordering = ['create_time']


class LLMProvider(BaseModel):
    name = models.CharField("Name", max_length=64, unique=False)
    temperature = models.DecimalField("Temperature", max_digits=3, decimal_places=2)
    frequency_penalty = models.DecimalField("Frequency penalty", max_digits=3, decimal_places=2)
    top_p = models.DecimalField("TopP",max_digits=3, decimal_places=2)
    chunk_length = models.PositiveIntegerField("Token length")
    description = models.TextField("Description", blank=True)
    config = models.JSONField('LLM configuration', default=dict, blank=True)  # {"Authorization":"Bearer xxx"}
    is_active = models.BooleanField("Is active", default=False)
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name='Creator',
        null=True,
        db_column='creator_id',  # Database column name is still creator_id
        related_name='llm_provider'
    )

    class Meta:
        db_table = "llm_provider"
        ordering = ['create_time']


class TestSample(BaseModel):
    uid = models.CharField("Business unique ID", max_length=64, unique=True, db_index=True)
    input = models.TextField("Input text")
    gold = models.TextField("Standard answer")
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name='Creator',
        null=True,
        db_column='creator_id',  # Database column name is still creator_id
        related_name='llm_test_sample'
    )

    class Meta:
        db_table = 'llm_test_sample'


class LLMTest(BaseModel):
    prompt = models.ForeignKey(
        Prompt,  # or 'api.app.llm.Prompt' depending on your app name
        on_delete=models.CASCADE,
        db_column='prompt_id',
        verbose_name='Prompt'
    )
    prompt_content_snapshot = models.TextField(
        verbose_name="Prompt content snapshot"
    )
    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        db_column='provider_id',
        verbose_name='LLM provider'
    )
    CHOICES = (
        (0, "Queuing"),
        (1, "Reviewing"),
        (2, "Review successful"),
        (3, "Review failed"),
    )
    status = models.IntegerField(choices=CHOICES,
                                 db_comment="0-Testing, 2-Test successful, 3-Test failed",
                                 default=0,
                                 help_text="0-Testing, 2-Test successful, 3-Test failed")
    # Add this line
    temperature = models.DecimalField("Temperature", max_digits=3, decimal_places=2)
    frequency_penalty = models.DecimalField("Frequency penalty", max_digits=3, decimal_places=2)
    top_p = models.FloatField("TopP")
    chunk_length = models.PositiveIntegerField("Token length")
    hit_rate = models.FloatField("Hit rate", blank=True, null=True)
    precision = models.FloatField("Precision", blank=True, null=True)
    recall = models.FloatField("Recall", blank=True, null=True)
    duration = models.FloatField("Review duration", blank=True, null=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name='Creator',
        null=True,
        db_column='creator_id',  # Database column name is still creator_id
        related_name='llm_test'
    )
    system_default = models.BooleanField("System default", default=False)

    class Meta:
        db_table = "llm_test_history"
        ordering = ['create_time']
