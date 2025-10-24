from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from services.models import ServiceOrder
from import_export.admin import ImportExportModelAdmin


class ServiceOrderInline(admin.TabularInline):
    """
    Displays a user's order history on their detail page.
    """
    model = ServiceOrder
    extra = 0  # Don't show empty forms for adding new orders here
    
    # --- FIX: Corrected field names to match your services/models.py ---
    fields = ('id', 'service', 'progress_status', 'created_at')
    readonly_fields = ('id', 'service', 'progress_status', 'created_at')

    can_delete = False # Prevent deleting orders from the user page
    show_change_link = True # Add a link to the full order detail page

    def has_add_permission(self, request, obj=None):
        # Disable the ability to add orders from the user page
        return False


class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    model = CustomUser
    # --- FIX: Added first_name and last_name to the list display ---
    list_display = ('customer_id', 'email', 'first_name', 'last_name', 'phone', 'is_staff', 'is_active','date_joined')
    list_filter = ('is_staff', 'is_active', 'user_type') # Added user_type for better filtering
    ordering = ('customer_id',)
    search_fields = ('customer_id', 'email', 'phone', 'first_name', 'last_name')

    inlines = [ServiceOrderInline]

    # --- FIX: Added a "Personal info" section to show name fields ---
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('customer_id', 'first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'user_type', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name', 'password', 'password2', 'is_staff', 'is_active')}
        ),
    )
    
    # Make the generated ID read-only
    readonly_fields = ('customer_id', 'date_joined')

    def get_queryset(self, request):
        # This function controls what is shown in the admin list.
        qs = super().get_queryset(request)
        # We only hide users that have a partner profile linked to them.
        return qs.filter(partner__isnull=True)



admin.site.register(CustomUser, CustomUserAdmin)

