# In core/admin_setup.py

from django.contrib import admin
from django.apps import apps
from import_export.admin import ImportExportModelAdmin

def auto_register_models():
    """
    Finds all models that have not been manually registered and provides them
    with a generic admin interface that includes import/export functionality.
    """
    # Get a list of all models from all installed apps.
    all_models = apps.get_models()
    
    for model in all_models:
        # This is the crucial check: if the model is NOT already registered, then proceed.
        if model not in admin.site._registry:
            
            # Create a generic admin class for this unregistered model.
            class GenericAdmin(ImportExportModelAdmin):
                # Display all the model's field names in the list view.
                list_display = [field.name for field in model._meta.fields]
                
            try:
                # Register the model with our new generic admin class.
                admin.site.register(model, GenericAdmin)
            except admin.sites.AlreadyRegistered:
                # This is a failsafe in case the model was registered by another process
                # between our check and this registration attempt.
                pass