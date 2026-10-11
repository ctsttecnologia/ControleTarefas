

# pgr_gestao/models_base.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from core.managers import FilialManager


class SoftDeleteFilialManager(FilialManager):
    def get_queryset(self):
        return super().get_queryset().filter(excluido_em__isnull=True)


class SoftDeleteModel(models.Model):
    excluido_em = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)
    excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    objects = SoftDeleteFilialManager()
    all_objects = models.Manager()   # auditoria e expurgo

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.excluido_em, self.excluido_por = timezone.now(), user
        self.save(update_fields=["excluido_em", "excluido_por"])
