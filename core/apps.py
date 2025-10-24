from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # 1. Update the import to get the new function name.
        from .admin_setup import auto_register_models

        # 2. Call the new, corrected function.
        auto_register_models()