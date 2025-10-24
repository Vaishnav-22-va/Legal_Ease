from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ServiceCategory, Service, ServiceOrder, RequiredDocument, OrderDocument,DynamicServiceField, ServiceNote,DynamicFieldResponse
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .views import service_order_chart 
from django.urls import path

# --- Inlines for the Admin Panel ---

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    prepopulated_fields = {'slug': ('title',)}

class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 1
    fields = ('name', 'description', 'is_mandatory')


class DynamicServiceFieldInline(admin.TabularInline):
    model = DynamicServiceField
    extra = 1 # Allows one extra blank field to be added

# NEW: An inline to display the documents uploaded by the user
class OrderDocumentInline(admin.TabularInline):
    model = OrderDocument
    extra = 0
    fields = ('document_name', 'view_file_link')
    readonly_fields = ('document_name', 'view_file_link')
    
    def view_file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.file.url)
        return "No file uploaded"

    view_file_link.short_description = "Uploaded Document"

    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
# NEW: Inline for Notes
class ServiceNoteInline(admin.TabularInline):
    model = ServiceNote
    extra = 1


# --- Admin Registration ---

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ImportExportModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order',)
    inlines = [ServiceInline]
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin):
    list_display = ('title', 'category', 'order', 'is_active', 'is_featured')
    list_filter = ('category', 'is_active', 'is_featured')
    ordering = ('category', 'order')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [RequiredDocumentInline,DynamicServiceFieldInline,ServiceNoteInline]
    fieldsets = (
        (None, {
            'fields': (
                'title', 'slug', 'category', 'icon_class', 'page_url', 'order',
                'short_description', 'long_description', 'icon', 'hero_image',
                'is_active', 'is_featured', 'available_for'
            )
        }),
        ('Pricing', {
            'fields': ('price_user', 'price_partner_default')
        }),
    )

class DynamicFieldResponseInline(admin.TabularInline):
    model = DynamicFieldResponse
    extra = 0
    # Make the question (field) read-only, but the answer (value) editable
    readonly_fields = ('field',) 
    fields = ('field', 'value')

    def has_add_permission(self, request, obj=None):
        return False # Don't allow adding new responses from the admin

    def has_delete_permission(self, request, obj=None):
        return False # Don't allow deleting responses
    

@admin.register(ServiceOrder)
class ServiceOrderAdmin(ImportExportModelAdmin):
    list_display = ('id', 'service', 'user', 'payment_status', 'progress_status', 'created_at')
    list_filter = ('payment_status', 'progress_status', 'created_at')
    search_fields = ('user__email', 'service__title', 'user__partner__partner_id')
    actions = ['mark_as_paid', 'mark_as_cancelled', 'mark_in_progress', 'mark_completed']
    
    inlines = [OrderDocumentInline,DynamicFieldResponseInline]

    readonly_fields = ('user', 'customer', 'service', 'price', 'payment_status', 'created_at')

    fieldsets = (
        ("Order & Customer Details", {
            "fields": (
                "service", 
                "price", 
                "user", 
                "customer", 
                "full_name",
                "email", 
                "phone",
                "additional_info",
                "created_at"
            )
        }),
        ("Admin Response & Final Documents", {
            "fields": (
                "returned_document", 
                "remarks", 
                "invoice",
                ("payment_status", "progress_status")
            )
        }),
    )


    

    # --- Payment Actions ---
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(payment_status='paid')
        self.message_user(request, f"{updated} order(s) marked as Paid.")
    mark_as_paid.short_description = "Mark selected orders as Paid"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(payment_status='cancelled')
        self.message_user(request, f"{updated} order(s) marked as Cancelled.")
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"

    def mark_in_progress(self, request, queryset):
        updated = queryset.update(progress_status='in_progress')
        self.message_user(request, f"{updated} order(s) marked as In Progress.")
    mark_in_progress.short_description = "Mark selected orders as In Progress"

    def mark_completed(self, request, queryset):
        updated = queryset.update(progress_status='completed')
        self.message_user(request, f"{updated} order(s) marked as Completed.")
    mark_completed.short_description = "Mark selected orders as Completed"

class ServiceOrderResource(resources.ModelResource):
    class Meta:
        model = ServiceOrder


# services/admin.py

