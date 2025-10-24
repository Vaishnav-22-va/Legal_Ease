# partners/admin.py
from django.urls import reverse
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from django.db import transaction
from services.models import ServiceOrder
from .forms import PartnerCreationForm
from import_export.admin import ImportExportModelAdmin
from .models import (
    PartnerPlan, Partner, PartnerSubscription, PartnerWallet, 
    WalletTransaction, PartnerRequest, DocumentType, 
    PartnerRequestDocument, Customer,  PartnerDocument
)
User = get_user_model()

# --- Configuration for Plans and Signup ---

@admin.register(PartnerPlan)
class PartnerPlanAdmin(ImportExportModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'duration_days')
    list_filter = ('plan_type',)
    search_fields = ('name',)

@admin.register(DocumentType)
class DocumentTypeAdmin(ImportExportModelAdmin):
    list_display = ('name',)

# --- Configuration for Partner Requests (Pre-Approval) ---

class PartnerRequestDocumentInline(admin.TabularInline):
    model = PartnerRequestDocument
    extra = 0
    fields = ('document_type', 'view_file_link')
    readonly_fields = ('document_type', 'view_file_link')

    def view_file_link(self, obj):
        if obj.file and hasattr(obj.file, 'url'):
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.file.url)
        return "No file uploaded"
    view_file_link.short_description = "Document Link"

    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(PartnerRequest)
class PartnerRequestAdmin(ImportExportModelAdmin):
    list_display = ('business_name', 'email', 'selected_plan', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'selected_plan__plan_type')
    search_fields = ('business_name', 'email', 'order_id')
    readonly_fields = ('created_at',)
    inlines = [PartnerRequestDocumentInline]
    actions = ['approve_selected_requests']

    
    
    
    @transaction.atomic
    def approve_selected_requests(self, request, queryset):
        """
        Admin action to approve selected partner requests and create all necessary accounts.
        """
        approved_count = 0
        for partner_request in queryset.filter(payment_status='paid'):
            try:
                # The create_user call with all arguments and the closing parenthesis
                user = User.objects.create_user(
                    email=partner_request.email,
                    password=partner_request.password,
                    phone=partner_request.phone
                )

                full_name_parts = partner_request.full_name.split()
                user.first_name = full_name_parts[0] if full_name_parts else ''
                user.last_name = ' '.join(full_name_parts[1:]) if len(full_name_parts) > 1 else ''
                
                # 3. Save the updated name fields to the user object
                user.save(update_fields=['first_name', 'last_name'])

                user.password = partner_request.password
                user.save()


                partner = Partner.objects.create(
                user=user, 
                business_name=partner_request.business_name,
                address=partner_request.address,
                city=partner_request.city,
                state=partner_request.state,
                pincode=partner_request.pincode
            )
                
                

                for doc in partner_request.documents.all():
                   PartnerDocument.objects.create(
                    partner=partner,
                    document_type=doc.document_type,
                    file=doc.file
                )
                
                # Creates the wallet and subscription
                PartnerWallet.objects.create(partner=partner)
                
                if partner_request.selected_plan:
                    PartnerSubscription.objects.create(partner=partner, plan=partner_request.selected_plan)

                approved_count += 1
            except Exception as e:
                self.message_user(request, f"Error approving {partner_request.business_name}: {e}", level='error')
    
        if approved_count > 0:
            self.message_user(request, f"Successfully approved {approved_count} partner(s).")

    approve_selected_requests.short_description = "Approve selected paid requests"



class PartnerDocumentInline(admin.TabularInline):
    model = PartnerDocument
    # Show one empty slot for a new document by default
    extra = 1 
    # These are the fields you need to upload a new document
    fields = ('document_type', 'file')

# --- Configuration for Approved Partners and their Data ---

class PartnerSubscriptionInline(admin.TabularInline):
    model = PartnerSubscription
    extra = 0
    readonly_fields = ('plan', 'start_date', 'end_date', 'is_active')
    can_delete = False

class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('timestamp', 'transaction_type', 'amount', 'details')
    can_delete = False
    def has_add_permission(self, request, obj=None): return False

class CustomerInline(admin.TabularInline):
    model = Customer
    extra = 0
    fields = ('full_name', 'email', 'phone')
    readonly_fields = ('full_name', 'email', 'phone')
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(PartnerWallet)
class PartnerWalletAdmin(ImportExportModelAdmin):
    list_display = ('partner', 'balance', 'updated_at')
    search_fields = ('partner__business_name',)
    inlines = [WalletTransactionInline]

    fields = ('partner', 'balance', 'balance_expires_at')
    readonly_fields = ('partner',)

    def save_model(self, request, obj, form, change):
        """
        Custom logic to create a transaction record on manual balance change.
        """
        # 'change' is True if we are editing an existing wallet
        if change:
            try:
                # Get the wallet's state *before* the change from the database
                old_wallet = PartnerWallet.objects.get(pk=obj.pk)
                old_balance = old_wallet.balance
                
                # 'obj.balance' is the new balance submitted by the admin
                new_balance = obj.balance
                
                # Calculate the difference
                difference = new_balance - old_balance

                # If the balance was actually changed, create a transaction
                if difference != 0:
                    WalletTransaction.objects.create(
                        wallet=obj,
                        transaction_type=WalletTransaction.TransactionType.ADMIN_ADJUSTMENT,
                        amount=difference,
                        details=f"Manual adjustment by admin: {request.user}"
                    )
            except PartnerWallet.DoesNotExist:
                # This case is unlikely but good to handle
                pass
        
        # Finally, call the original save method to save the wallet object
        super().save_model(request, obj, form, change)



@admin.register(Partner)
class PartnerAdmin(ImportExportModelAdmin):
    # --- Form to use ONLY on the 'Add partner' page ---
    add_form = PartnerCreationForm

    # --- Fields for the 'Add partner' page ---
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password', 'full_name', 'phone', 
                'business_name', 'address', 'city', 'state', 'pincode','subscription_plan',
            ),
        }),
    )

    # --- Your original fields for the 'Change partner' (edit) page ---
    fieldsets = (
        ('Partner Information', {
            'fields': (
                'business_name', 'partner_id', 
                ('user_email', 'user_phone'), 
                'address','city', 'state', 'pincode',
                'view_order_history_link','view_wallet_details_link',
            )
        }),
    )

    # Read-only fields for the 'Change' (edit) page
    readonly_fields = ('partner_id', 'user_email','user_full_name', 'user_phone', 'view_order_history_link','view_wallet_details_link')
    
    
    # --- General Admin Configuration ---
    list_display = ('business_name','user_full_name', 'partner_id', 'user_email', 'user_phone', 'get_wallet_balance', 'has_active_access')
    search_fields = ('business_name', 'user__email', 'partner_id')
    inlines = [PartnerDocumentInline, PartnerSubscriptionInline, CustomerInline]

    # This method dynamically shows the correct fields for adding vs. editing
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)
    
    # This method loads the correct form for the 'Add' page
    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            kwargs['form'] = self.add_form
        return super().get_form(request, obj, **kwargs)

    # --- Core Logic to Save a Manually Added Partner ---
    def save_model(self, request, obj, form, change):
        if not change:  # This logic runs ONLY when creating a new partner
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            
            user = None
            existing_user = User.objects.filter(email=email).first()

            if existing_user:
                # If user exists, check they aren't already a partner (due to your OneToOneField)
                if hasattr(existing_user, 'partner'):
                    self.message_user(request, f"User with email {email} is already linked to a partner profile.", level='error')
                    return # Stop the save process
                user = existing_user
            else:
                # If user does not exist, create a new one
                user = User.objects.create_user(email=email, password=password, phone=phone)
                name_parts = full_name.split()
                user.first_name = name_parts[0] if name_parts else ''
                user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                user.save()

            # 1. Link the user (found or new) to the Partner object
            obj.user = user
            super().save_model(request, obj, form, change) # Saves the Partner, which also generates the partner_id via its own .save() method

            # 2. Create the mandatory PartnerWallet
            PartnerWallet.objects.create(partner=obj)

            # 3. Create the initial subscription if a plan was selected
            plan = form.cleaned_data.get('subscription_plan')
            if plan:
                # Your PartnerSubscription model's .save() method will handle wallet credits and dates
                PartnerSubscription.objects.create(partner=obj, plan=plan, is_active=True)

        else: # This runs when updating an existing partner
            super().save_model(request, obj, form, change)

            # --- NEW METHOD TO CREATE THE WALLET LINK ---
    @admin.display(description='Wallet Details')
    def view_wallet_details_link(self, obj):
        # Check if the partner has a wallet yet
        if not hasattr(obj, 'wallet'):
            return "No wallet found."
        
        # Build the URL to that specific wallet's admin page
        wallet_url = reverse(
            "admin:partner_partnerwallet_change", 
            args=[obj.wallet.pk]
        )
        # Create a clickable HTML link
        return format_html('<a href="{}">View Wallet & Transactions</a>', wallet_url)

    # --- Your existing display methods ---
    @admin.display(description='Partner Name', ordering='user__first_name')
    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    @admin.display(description='Email')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description='Phone')
    def user_phone(self, obj):
        return obj.user.phone

    @admin.display(description='Wallet Balance', ordering='wallet__balance')
    def get_wallet_balance(self, obj):
        if hasattr(obj, 'wallet'):
            return f"₹{obj.wallet.balance}"
        return "N/A"
    
    @admin.display(description='Order History')
    def view_order_history_link(self, obj):
        count = ServiceOrder.objects.filter(user=obj.user).count()
        if count == 0:
            return "No orders found."
        url = (
            reverse("admin:services_serviceorder_changelist")
            + f"?user__id__exact={obj.user.id}"
        )
        return format_html('<a href="{}">View {} Orders</a>', url, count)

    @admin.display(description='Partner Name', ordering='user__first_name')
    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    @admin.display(description='Email')
    def user_email(self, obj):
        return obj.user.email

    # New method to display the phone number
    @admin.display(description='Phone')
    def user_phone(self, obj):
        return obj.user.phone

    @admin.display(description='Wallet Balance', ordering='wallet__balance')
    def get_wallet_balance(self, obj):
        if hasattr(obj, 'wallet'):
            return f"₹{obj.wallet.balance}"
        return "N/A"
    
    @admin.display(description='Order History')
    def view_order_history_link(self, obj):
        count = ServiceOrder.objects.filter(user=obj.user).count()
        if count == 0:
            return "No orders found."
        
        # Create the URL for the ServiceOrder admin list, filtered by this partner's user ID
        url = (
            reverse("admin:services_serviceorder_changelist")
            + f"?user__id__exact={obj.user.id}"
        )
        return format_html('<a href="{}">View {} Orders</a>', url, count)
    


@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'partner')
    list_filter = ('partner',)
    search_fields = ('full_name', 'email', 'partner__business_name')
    readonly_fields = ('partner_customer_id',)

# Register other models for basic viewing
admin.site.register(PartnerSubscription)
admin.site.register(WalletTransaction)
