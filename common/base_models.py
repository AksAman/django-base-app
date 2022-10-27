from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseDjangoModel(models.Model):

    create_date = models.DateTimeField(_("Create Date/Time"), default=timezone.now)
    update_date = models.DateTimeField(_("Date/Time Modified"), default=timezone.now)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """On save, update timestamps"""
        if not self.pk:
            self.create_date = timezone.now()
        self.update_date = timezone.now()

        super().save(*args, **kwargs)
