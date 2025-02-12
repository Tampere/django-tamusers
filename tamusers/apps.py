from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TamusersConfig(AppConfig):
    name = 'tamusers'
    verbose_name = _("Tampere Users")
