from django.db import models

class ParamLink(models.Model):
    string = models.CharField(max_length=1000)
    consulted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'worker'
