# services/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponseBadRequest
from decimal import Decimal

# App-specific imports
from .models import Service, ServiceOrder, ServiceCategory, OrderDocument
from .forms import ServiceOrderForm
from .utils import generate_invoice

# Cross-app imports
from partner.models import Partner, Customer, PartnerWallet, WalletTransaction, PartnerPlan




# --- Core Service Browsing Views ---

def service_list(request):
    categories = ServiceCategory.objects.prefetch_related('services').all()
    customer_id = request.GET.get('customer_id')

    is_partner_logged_in = False
    if request.user.is_authenticated and hasattr(request.user, 'partner'):
        is_partner_logged_in = True

        
    
    context = {
        "categories": categories,
        "customer_id": customer_id,
        "is_partner_logged_in": is_partner_logged_in, # <-- FIX: This line was missing
    }
    return render(request, "services/service_list.html", context)

# ... rest of your views.py file

def service_info(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    required_documents = service.required_documents.all()
    customer_id = request.GET.get('customer_id')
    is_partner = request.user.is_authenticated and hasattr(request.user, 'partner')

    # ✅ --- NEW REDIRECT LOGIC ---
    # If the user is a partner and no customer_id is in the URL,
    # redirect them to the customer selection page immediately.
    if is_partner and not customer_id:
        # We store the intended service slug in the session to redirect them back later.
        request.session['next_service_slug'] = slug 
        messages.info(request, "Please select a customer to proceed with this service.")
        return redirect('partner:select_customer_for_order')
    # --- END OF NEW LOGIC ---
    
    # Default to B2C pricing
    price = service.get_price_for_user()
    is_partner_logged_in = False

    # If user is a partner, update the price and the flag
    if request.user.is_authenticated and hasattr(request.user, 'partner'):
        is_partner_logged_in = True
        price = service.price_partner_default

    # If user is a partner, determine their specific price
    if request.user.is_authenticated and hasattr(request.user, 'partner'):
        is_partner_logged_in = True
        price = service.price_partner_default

    # Advanved SEO for Google
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": service.title,
        "description": service.short_description,
        "provider": {
            "@type": "Organization",
            "name": "Legal Munshi"
        },
        "offers": {
            "@type": "Offer",
            "price": str(service.price_user), # Price ko string mein convert karein
            "priceCurrency": "INR"
        }
    }

    context = {
        "service": service,
        "price": price,
        "required_documents": required_documents,
        "customer_id": customer_id,
        "is_partner_logged_in": is_partner_logged_in,
        "structured_data_dict": structured_data
    }

    
    return render(request, "services/service_info.html", context)

# --- Unified Order Creation View ---

@login_required
def service_order_create(request, slug):
    """
    A single view to handle service order creation for both B2C and Partners.
    """
    service = get_object_or_404(Service, slug=slug, is_active=True)
    required_documents = service.required_documents.all()
    is_partner = hasattr(request.user, 'partner')
    
    # Get the dynamic fields and notes from the service object
    dynamic_fields = service.dynamic_fields.all()
    dynamic_notes = service.notes.all()


    customer = None
    initial_data = {}

    if is_partner:
        partner = request.user.partner
        customer_id = request.GET.get('customer_id')
        if not customer_id:
            messages.error(request, "Please select a customer for this order.")
            return redirect('partner:select_customer_for_order')
        customer = get_object_or_404(Customer, id=customer_id, partner=partner)
        price = service.price_partner_default
        initial_data = {'full_name': customer.full_name, 'email': customer.email, 'phone': customer.phone}
    else:
        price = service.get_price_for_user()
        initial_data = {'full_name': request.user.get_full_name(), 'email': request.user.email, 'phone': request.user.phone}

    if request.method == 'POST':
        # Pass dynamic_fields and required_docs to the form
        form = ServiceOrderForm(
            request.POST,
            request.FILES,
            required_docs=required_documents,
            dynamic_fields=dynamic_fields
        )
        if form.is_valid():
            order = form.save(commit=False)
            order.service = service
            order.user = request.user
            order.price = price
            order.customer = customer
            
            # Save dynamic field responses
            dynamic_responses = {}
            for field in dynamic_fields:
                field_name = f'dynamic_field_{slugify(field.name)}'
                dynamic_responses[field.name] = form.cleaned_data.get(field_name)
                
                
                order.dynamic_field_responses = dynamic_responses
            order.save()

            for doc in required_documents:
                field_name = f'document_{slugify(doc.name)}'
                uploaded_file = request.FILES.get(field_name)
                if uploaded_file:
                    OrderDocument.objects.create(order=order, document_name=doc.name, file=uploaded_file)
            
            messages.success(request, "Application submitted. Please proceed to payment.")
            return redirect('services:checkout', order_id=order.pk)
    else:
        # Pass dynamic_fields and required_docs to the form on GET
        form = ServiceOrderForm(
            initial=initial_data,
            required_docs=required_documents,
            dynamic_fields=dynamic_fields
        )

    return render(request, "services/service_form.html", {
        "service": service,
        "form": form,
        "price": price,
        "customer": customer,
        "dynamic_notes": dynamic_notes,
    })

# --- Smart Payment Flow Views ---

@login_required
def service_checkout(request, order_id):
    """
    Displays the correct payment options based on the user type (B2C vs. Partner).
    """
    order = get_object_or_404(ServiceOrder, pk=order_id, user=request.user)
    context = {'order': order}
    
    if hasattr(request.user, 'partner'):
        partner = request.user.partner
        active_subscription = partner.subscriptions.filter(is_active=True).first()
        wallet, created = PartnerWallet.objects.get_or_create(partner=partner)
        
        context['is_partner'] = True
        context['wallet_balance'] = wallet.balance
        context['plan_type'] = active_subscription.plan.plan_type if active_subscription else None
    
    return render(request, 'services/checkout.html', context)

@login_required
@transaction.atomic
def process_service_payment(request, order_id):
    """
    Processes the chosen payment method (wallet or gateway).
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    order = get_object_or_404(ServiceOrder, pk=order_id, user=request.user)
    payment_method = request.POST.get('payment_method')

    if payment_method == 'wallet':
        partner = request.user.partner
        wallet = partner.wallet
        if wallet.balance >= order.price:
            wallet.balance -= order.price
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.SERVICE_PAYMENT,
                amount=-order.price,
                details=f"Payment for Service Order #{order.id}"
            )
            order.payment_status = 'paid'
            order.payment_method = 'wallet'
            order.save()
            generate_invoice(order)
            messages.success(request, "Payment successful! Your order has been placed.")
            return redirect('accounts:orders')
        else:
            messages.error(request, "Insufficient wallet balance.")
            return redirect('partner:wallet_top_up')

    elif payment_method == 'gateway':
        return redirect(f"{reverse('payments:payment_page')}?order_id={order.id}&amount={order.price}&purpose=service")

    messages.error(request, "Invalid payment method selected.")
    return redirect('services:checkout', order_id=order.id)




from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from .models import ServiceOrder # Make sure ServiceOrder is imported

# ... your other views ...

@staff_member_required
def service_order_chart(request):
    """
    Provides data for the service order chart in the admin dashboard.
    """
    # Query to count service orders grouped by the day they were created
    chart_data = (
        ServiceOrder.objects
        .annotate(date=TruncDay('created_at')) # Assumes your model has a 'created_at' field
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    # Format the data into lists that Chart.js can read
    labels = [data['date'].strftime('%b %d, %Y') for data in chart_data]
    counts = [data['count'] for data in chart_data]
    
    return JsonResponse({
        'labels': labels,
        'data': counts,
    })