from django.db import models

class Task(models.Model):
    external_id = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=255)
    due_date = models.DateField(blank=True, null=True)
    estimated_hours = models.FloatField(default=1.0)
    importance = models.IntegerField(default=5)
    dependencies = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title
