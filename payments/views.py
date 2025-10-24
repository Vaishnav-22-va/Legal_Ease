# payments/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
# Import the necessary models
from services.models import ServiceOrder
from partner.models import PartnerRequest, PartnerWallet, WalletTransaction
from partner.models import Partner # Assuming this model is in partners.models
from services.utils import generate_invoice



# -----------------------------
# Payment Page
# -----------------------------
def payment_page(request):
    """
    Universal payment page that validates all required parameters before rendering.
    """
    order_id = request.GET.get("order_id")
    amount_str = request.GET.get("amount")
    purpose = request.GET.get("purpose")
    plan_id = request.GET.get("plan_id")

    # 1. Check if all parameters exist
    if not all([order_id, amount_str, purpose]):
        messages.error(request, "The payment link is invalid or incomplete. Please try again.")
        return redirect('partner:dashboard') # Redirect to a safe page

    # 2. Try to convert amount to a Decimal
    try:
        amount_decimal = Decimal(amount_str)
    except InvalidOperation:
        messages.error(request, "An invalid amount was specified in the payment link.")
        return redirect('partner:dashboard') # Redirect to a safe page
        
    # 3. If all checks pass, build the context and render the template
    context = {
        "order_id": order_id,
        "amount": amount_decimal,
        "purpose": purpose,
        "plan_id": plan_id,
        # You can add your Razorpay Key here if it's in settings
        # "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID, 
    }
    return render(request, "payments/payment.html", context)


# -----------------------------
# Payment Success
# -----------------------------
def payment_success(request, order_id):
    """
    Payment success callback handler.
    Determines the purpose of the payment and redirects to the correct app-specific handler.
    """
    purpose = request.GET.get('purpose')
    amount = request.GET.get('amount')
    plan_id = request.GET.get('plan_id')
    

    if not order_id:
        return HttpResponseBadRequest("Missing order_id parameter.")

    if purpose == 'plan_purchase':
        try:
            PartnerRequest.objects.get(order_id=order_id)
            callback_url = f"{reverse('partner:payment_callback')}?order_id={order_id}"
            return redirect(callback_url)
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Invalid order ID for a partner plan.")
    
    elif purpose == 'service':
        try:
            ServiceOrder.objects.get(pk=order_id)
            return redirect(reverse('payments:service_success', kwargs={'order_id': order_id}))
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Invalid order ID for a service.")

    # --- Routing for Partner Wallet Top-Up ---
    elif purpose == 'wallet_topup':
        # This is for existing partners.
        # We redirect to the NEW callback view in the partner app.
        callback_url = f"{reverse('partner:payment_success')}?order_id={order_id}&purpose={purpose}&amount={amount}"
        return redirect(callback_url)
    
    elif purpose == 'plan_upgrade':
        # This handles the new upgrade flow
        # It redirects to the same final callback, but passes the plan_id along
        if not plan_id:
            return HttpResponseBadRequest("Missing plan_id for plan upgrade.")
        callback_url = f"{reverse('partner:payment_success')}?order_id={order_id}&purpose={purpose}&amount={amount}&plan_id={plan_id}"
        return redirect(callback_url)



# -----------------------------
# Service-specific payment views
# -----------------------------

def service_payment_page(request):
    """
    A view to render a checkout page specifically for services.
    (This was the missing function causing the error).
    """
    return render(request, "payments/service_checkout.html")

def service_payment_success(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id)
    
    if order.payment_status != 'paid':
        order.payment_status = 'paid'
        order.payment_method = 'gateway'
        order.save()

    if not order.invoice:
        generate_invoice(order)
        order.refresh_from_db()

    return render(request, "payments/payment_success.html", {"order": order})

def service_payment_failed(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id)
    return render(request, "payments/service_failed.html", {"order": order})
