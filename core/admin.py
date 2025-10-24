from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import CallbackRequest

def auto_register_import_export_for_all_models():
    """
    Dynamically registers all admin models with ImportExportModelAdmin.
    
    This function should be called from the AppConfig's ready() method.
    """
    processed_count = 0
    # Iterate over a copy of the registry to avoid modification issues
    # The registry is a dictionary of {model: ModelAdmin}
    for model, model_admin in list(admin.site._registry.items()):
        
        # Check if the model is already registered with ImportExportModelAdmin
        # We use isinstance to check inheritance
        if isinstance(model_admin, ImportExportModelAdmin):
            continue

        # Dynamically create a Resource class for the current model.
        class DynamicResource(resources.ModelResource):
            class Meta:
                model = model
                
        # Create a new, temporary class that inherits from both
        # the original ModelAdmin and ImportExportModelAdmin.
        class TempModelAdmin(ImportExportModelAdmin, model_admin.__class__):
            # Assign the new resource class to the temporary class.
            resource_class = DynamicResource

            # We need to copy any custom methods or attributes from the original
            # admin class to the new temporary class.
            # This is a key step to prevent losing customizations.
            for attr_name in dir(model_admin.__class__):
                if not hasattr(TempModelAdmin, attr_name) and not attr_name.startswith('_'):
                    setattr(TempModelAdmin, attr_name, getattr(model_admin.__class__, attr_name))

        # Unregister the original model admin and register the new one.
        admin.site.unregister(model)
        admin.site.register(model, TempModelAdmin)
        
        processed_count += 1
    
    print(f"Successfully auto-registered {processed_count} models for import-export.")

   

@admin.register(CallbackRequest)
class CallbackRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile_no', 'subject', 'created_at')
    search_fields = ('name', 'mobile_no', 'subject')

from django.contrib import admin
from .models import MediaCategory, MediaItem

@admin.register(MediaCategory)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')

@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_highlighted', 'order')
    list_filter = ('category', 'is_highlighted')
    search_fields = ('title',)
