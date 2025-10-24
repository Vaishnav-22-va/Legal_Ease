# partners/views.py

import json
import random
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import WalletTopUpForm
# Local app imports
from services.models import ServiceOrder
from .models import (
    PartnerPlan, PartnerRequest, PartnerRequestDocument, DocumentType, 
    Partner, PartnerWallet, PartnerSubscription, WalletTransaction, Customer
)
from django.utils.crypto import get_random_string 
from django.core.mail import send_mail
from django.conf import settings
from accounts.utils import send_otp_email 
from .forms import CustomerEditForm
from django.views.decorators.http import require_POST



# Get the custom user model
User = get_user_model()

def generate_otp():
    return str(random.randint(100000, 999999))


# --- Utility Functions ---

def _get_json_data(request):
    """Helper to safely parse JSON body."""
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}

# --- AJAX OTP and Validation Views ---

@csrf_exempt
def ajax_send_otp(request):
    """
    Handles sending OTP to an email for signup, mirroring the password reset flow.
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

    data = _get_json_data(request)
    contact_type = data.get('type')
    email = data.get('value', '').strip()

    if not email or contact_type != 'email':
        return JsonResponse({"success": False, "message": "Invalid data provided."}, status=400)

    # For signup, we must ensure the user does NOT already exist.
    if User.objects.filter(email=email, partner__isnull=False).exists():
        return JsonResponse({"success": False, "message": "A partner with this email already exists."}, status=400)

    # Generate a 6-digit OTP
    otp = get_random_string(length=6, allowed_chars="0123456789")
    
    # Store the OTP in the session for later verification.
    # We'll use a specific key to avoid conflicts.
    request.session['signup_otp'] = otp
    request.session['signup_otp_email'] = email # Store email to verify against
    
    # Set a session expiry for the OTP, e.g., 5 minutes (300 seconds)
    request.session.set_expiry(300)

    try:
        send_otp_email(email, otp, context="Partner Signup")
        return JsonResponse({"success": True, "message": "An OTP has been sent to your email."})
    except Exception as e:
        # In a real application, you would log this error
        print(f"Error sending signup email: {e}")
        return JsonResponse({"success": False, "message": "Failed to send OTP email."}, status=500)


@csrf_exempt
def ajax_verify_otp(request):
    """
    Verifies the OTP submitted by the user during signup.
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

    data = _get_json_data(request)
    otp_entered = data.get('otp', '').strip()
    
    # Retrieve OTP from session
    session_otp = request.session.get('signup_otp')

    if not session_otp:
        return JsonResponse({"success": False, "message": "OTP has expired or was not sent. Please request a new one."}, status=400)

    if session_otp == otp_entered:
        # OTP is correct. Clear it from the session to prevent reuse.
        del request.session['signup_otp']
        del request.session['signup_otp_email']
        return JsonResponse({"success": True, "message": "OTP verified successfully."})
    else:
        return JsonResponse({"success": False, "message": "The OTP you entered is incorrect."}, status=400)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def check_partner_existence(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"exists": False, "message": "Invalid data."}, status=400)

        email = data.get("email")
        phone = data.get("phone")

        exists = False
        messages = []

        if email:
            if Partner.objects.filter(user__email=email).exists():
                exists = True
                messages.append("Email is already registered with another partner.")

        if phone:
            if Partner.objects.filter(user__phone=phone).exists():
                exists = True
                messages.append("Phone number is already registered with another partner.")

        return JsonResponse({"exists": exists, "message": " ".join(messages)})

    return JsonResponse({"exists": False, "message": ""})


# --- Partner Signup and Payment Flow ---

def partner_signup(request):
    """Displays the main partner signup page with a static form."""
    plans = PartnerPlan.objects.all()
    # Static list of states for the dropdown in your HTML
    states = ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal']
    required_docs = DocumentType.objects.all()
    
    context = {
        'plans': plans,
        'states': states,
        'required_docs': required_docs,
    }
    return render(request, 'partner/signup.html', context)

@csrf_exempt
@transaction.atomic
def ajax_signup_submit(request):
    """Handles partner signup via AJAX safely with proper validations."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

    # --- CORRECTED: Get data from request.POST instead of JSON ---
    full_name = request.POST.get('full_name', '').strip()
    business_type = request.POST.get('business_type', 'individual')
    business_name = request.POST.get('business_name', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    pincode = request.POST.get('pincode', '').strip()
    address = request.POST.get('address', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    selected_plan_id = request.POST.get('selected_plan_id') # This comes from your JS

    # --- Basic Validations ---
    if not all([full_name, phone, email, password, selected_plan_id]):
        return JsonResponse({"success": False, "message": "Please fill all required fields."}, status=400)


    # Check if partner with email or phone already exists
    if User.objects.filter(email=email, partner__isnull=False).exists():
        return JsonResponse({"success": False, "message": "This email is already registered to another partner."}, status=400)
    if User.objects.filter(phone=phone, partner__isnull=False).exists():
        return JsonResponse({"success": False, "message": "This phone number is already registered to another partner."}, status=400)


    # Check if selected plan exists
    try:
        selected_plan = PartnerPlan.objects.get(id=selected_plan_id)
    except PartnerPlan.DoesNotExist:
        return JsonResponse({"success": False, "message": "Selected plan does not exist."}, status=400)

    # --- Create PartnerRequest ---
    try:
        partner_request = PartnerRequest.objects.create(
            full_name=full_name,
            business_type=business_type,
            business_name=business_name,
            city=city,
            state=state,
            pincode=pincode,
            address=address,
            phone=phone,
            email=email,
            password=make_password(password),
            selected_plan=selected_plan
        )

        # Process and save documents
        for field_name, file in request.FILES.items():
            try:
                # The field name in the HTML is 'doc_{{ doc.id }}'
                doc_id = field_name.split('_')[-1]
                doc_type = DocumentType.objects.get(id=doc_id)
            except (IndexError, DocumentType.DoesNotExist):
                # This handles cases where a file field name doesn't match the expected format
                return JsonResponse({"success": False, "message": f"Unknown document type for field: {field_name}"}, status=400)

            PartnerRequestDocument.objects.create(
                partner_request=partner_request,
                document_type=doc_type,
                file=file
            )



        # Generate order_id for payment
        order_id = f'plan_{partner_request.id}_{random.randint(1000, 9999)}'
        partner_request.order_id = order_id
        partner_request.save()

        # Prepare redirect URL for payment
        amount = selected_plan.price
        payment_url = reverse('payments:payment_page') + f'?order_id={order_id}&amount={amount}&purpose=plan_purchase'

        return JsonResponse({"success": True, "redirect_url": payment_url})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

    
@csrf_exempt
@transaction.atomic
def step2_upload_docs(request):
    """Handles document uploads for Partner Signup Step 2."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

    try:
        partner_id = request.POST.get("partner_id")
        partner = PartnerRequest.objects.get(id=partner_id)

        for field_name, file in request.FILES.items():
            # Find matching DocumentType by name (case-insensitive)
            try:
                doc_type = DocumentType.objects.get(name__iexact=field_name)
            except DocumentType.DoesNotExist:
                return JsonResponse({"success": False, "message": f"Unknown document type: {field_name}"}, status=400)

            PartnerRequestDocument.objects.create(
                partner_request=partner,
                document_type=doc_type,
                file=file
            )

        return JsonResponse({"success": True, "message": "Documents uploaded successfully."})

    except PartnerRequest.DoesNotExist:
        return JsonResponse({"success": False, "message": "Invalid partner request ID."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
    


@transaction.atomic
def partner_payment_callback(request):
    """
    Handles the callback after a successful plan payment.
    Now only marks payment as 'paid' and redirects to the waiting page.
    """
    order_id = request.GET.get('order_id')
    
    try:
        partner_request = PartnerRequest.objects.get(order_id=order_id, payment_status='pending')
        partner_request.payment_status = 'paid'
        partner_request.save()

        # Redirect to a page that tells the user to wait for admin approval
        return redirect('partner:waiting_for_approval')

    except PartnerRequest.DoesNotExist:
        messages.error(request, "Invalid payment order.")
        return redirect('partner:signup')

def waiting_for_approval_view(request):
    """Renders a page telling the user to wait for manual approval."""
    return render(request, 'partner/waiting_for_approval.html')


# --- Partner Dashboard, Wallet, Orders, and Customers ---

def partner_dashboard(request):
    """Displays the main dashboard for a logged-in partner."""
    partner = get_object_or_404(Partner, user=request.user)

    is_partner = hasattr(request.user, 'partner')

    
    # --- Calculate stats and pass them to the template ---
    wallet_balance = partner.wallet.balance if hasattr(partner, 'wallet') else 0
    total_customers = Customer.objects.filter(partner=partner).count()
    total_orders = ServiceOrder.objects.filter(user=request.user).count() # Uncomment when ServiceOrder is available

    context = {
        'partner': partner,
        'wallet_balance': wallet_balance,
        'total_customers': total_customers,
        'total_orders': total_orders, # Uncomment when ServiceOrder is available
        'is_partner': is_partner,
    }
    return render(request, 'partner/dashboard.html', context)



@login_required
def upgrade_plan(request):
    """
    Allows a partner to view available plans and subscribe to a new one.
    """
    if not hasattr(request.user, 'partner'):
        messages.error(request, "You must be a partner to access this page.")
        return redirect('core:home')

    current_subscription = request.user.partner.subscriptions.filter(is_active=True).first()
    plans = PartnerPlan.objects.all().order_by('price')

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        if not plan_id:
            messages.error(request, "Please select a plan.")
            return redirect('partner:upgrade_plan')

        selected_plan = PartnerPlan.objects.get(id=plan_id)

        # Create a new subscription instance
        # This will automatically handle the wallet credit/expiration logic
        # if the plan type is WALLET_CREDIT
        new_subscription = PartnerSubscription.objects.create(
            partner=request.user.partner,
            plan=selected_plan,
            is_active=True,
        )

        # Redirect to the mock payment view for the new subscription
        return redirect(reverse('payments:mock_payment_with_id', kwargs={
            'amount': selected_plan.price,
            'purpose': 'plan_purchase',
            'related_id': new_subscription.pk # Use the new subscription's ID
        }))

    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'partner/upgrade_plan.html', context)


@login_required
def top_up_wallet(request):
    """
    Allows a partner to enter an amount and proceed to payment to top up their wallet.
    """
    if not hasattr(request.user, 'partner'):
        messages.error(request, "You must be a partner to access this page.")
        return redirect('core:home') # Or your home page

    if request.method == 'POST':
        form = WalletTopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # Generate a unique order_id for this transaction
            order_id = f"topup_{request.user.partner.id}_{random.randint(1000, 9999)}"
            
            # Redirect to your payment page with details
            payment_url = reverse('payments:payment_page') + f'?order_id={order_id}&amount={amount}&purpose=wallet_topup'
            return redirect(payment_url)
    else:
        form = WalletTopUpForm()

    return render(request, 'partner/wallet_top_up.html', {'form': form})


@login_required
def wallet_details(request):
    partner = get_object_or_404(Partner, user=request.user)
    
    # This will get the wallet if it exists, or create it if it doesn't.
    # The 'created' variable is a boolean (True/False) that we don't need here.
    wallet, created = PartnerWallet.objects.get_or_create(partner=partner)
    
    transactions = wallet.transactions.order_by('-timestamp')
    context = { 'wallet': wallet, 'transactions': transactions }
    return render(request, 'partner/wallet_details.html', context)

@login_required
def my_plan_details(request):
    """
    Displays the partner's current active plan details.
    """
    partner = get_object_or_404(Partner, user=request.user)
    current_subscription = partner.subscriptions.filter(is_active=True).first()
    
    context = {
        'subscription': current_subscription
    }
    return render(request, 'partner/my_plan_details.html', context)


@login_required
def upgrade_plan(request):
    """
    Allows a partner to view available plans and select one to purchase.
    """
    partner = get_object_or_404(Partner, user=request.user)
    current_subscription = partner.subscriptions.filter(is_active=True).first()
    plans = PartnerPlan.objects.all().order_by('price')

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        try:
            selected_plan = PartnerPlan.objects.get(id=plan_id)
        except PartnerPlan.DoesNotExist:
            messages.error(request, "Invalid plan selected.")
            return redirect('partner:upgrade_plan')

        # Generate a unique order ID for this upgrade
        order_id = f"upgrade_{partner.id}_{plan_id}_{random.randint(1000, 9999)}"
        amount = selected_plan.price
        
        # We now pass plan_id in the URL to use it in the callback after payment.
        payment_url = reverse('payments:payment_page') + f'?order_id={order_id}&amount={amount}&purpose=plan_upgrade&plan_id={plan_id}'
        return redirect(payment_url)

    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'partner/upgrade_plan.html', context)



@login_required
def partner_orders(request):
    """Placeholder view for listing partner's service orders."""
    return render(request, 'partner/orders.html')

@login_required
def partner_order_detail(request, order_id):
    """Placeholder view for a single order detail."""
    return render(request, 'partner/order_detail.html', {'order_id': order_id})

# partners/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Partner, Customer
from django.db import transaction

@login_required
@transaction.atomic
def partner_customers(request):
    """
    View for listing a partner's customers and handling the 'add new customer' form submission.
    """
    # Get the logged-in partner
    partner = get_object_or_404(Partner, user=request.user)
    
    # Handle the form submission for adding a new customer
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        # --- Form Validation ---
        if not all([full_name, email, phone]):
            messages.error(request, "Please fill in all required fields (Full Name, Email, Phone).")
            return redirect('partner:customers')
        
        # --- Check for existing customer to prevent duplicates per partner ---
        if Customer.objects.filter(partner=partner, email=email).exists():
            messages.error(request, "A customer with this email already exists for your account.")
            return redirect('partner:customers')

        try:
            # Create the new customer and link them to the logged-in partner
            Customer.objects.create(
                partner=partner,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address
            )
            messages.success(request, "Customer added successfully!")
            return redirect('partner:customers')

        except Exception as e:
            messages.error(request, f"An error occurred while saving the customer: {str(e)}")
            return redirect('partner:customers')

    # If it's a GET request, just display the customers page with the list
    customers = Customer.objects.filter(partner=partner).order_by('full_name')
    context = {
        'customers': customers
    }
    return render(request, 'partner/customers.html', context)

@login_required
def select_customer_for_order(request):
    """View for selecting a customer before creating an order."""
    partner = get_object_or_404(Partner, user=request.user)
    customers = Customer.objects.filter(partner=partner)
    return render(request, 'partner/select_customer_for_order.html', {'customers': customers})


# --- Login View ---

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # ❗ ADD THIS BLOCK TO DEBUG ❗
        print(f"--- Step 3 (Login Attempt): Trying to log in with email: '{email}'")
        try:
            user_in_db = User.objects.get(email=email)
            print(f"--- User '{email}' found in database.")
            print(f"--- Stored password hash is: '{user_in_db.password}'")
        except User.DoesNotExist:
            print(f"--- User '{email}' was NOT found in the database!")
        # ❗ END OF DEBUG BLOCK ❗
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            try:
                # SOLUTION: The existence of 'user.partner' is enough to confirm approval.
                user.partner  # This will raise ObjectDoesNotExist if no partner profile exists.
                login(request, user)
                # Make sure 'some_partner_dashboard_url' is a valid URL name.
                return redirect('partner:dashboard') 
            except ObjectDoesNotExist:
                # This case handles both non-partners and partners pending approval.
                error = "Your partner account is pending approval or does not exist."
                return render(request, 'partner/login.html', {'error': error})
        else:
            print("--- AUTHENTICATION FAILED ---") # Added for clarity
            error = "Invalid credentials. Please try again."

        return render(request, 'partner/login.html', {'error': error})

    return render(request, 'partner/login.html')


@login_required
@transaction.atomic
def payment_success_callback(request):
    """
    Handles successful payments for wallet top-ups for existing partners.
    This is the final step where the database is updated.
    """
    order_id = request.GET.get('order_id')
    amount_str = request.GET.get('amount')
    purpose = request.GET.get('purpose')
    
    if not hasattr(request.user, 'partner'):
        messages.error(request, "User is not a valid partner.")
        return redirect('core:home') # Or your main home page

    partner = request.user.partner

    if not all([order_id, amount_str, purpose]):
        messages.error(request, "Invalid payment callback received.")
        return redirect('partner:dashboard')

    try:
        amount = Decimal(amount_str)
    except (ValueError, TypeError):
        messages.error(request, "Invalid amount in payment callback.")
        return redirect('partner:dashboard')

    if purpose == 'wallet_topup':
        wallet, created = PartnerWallet.objects.get_or_create(partner=partner)
        
        wallet.balance += amount
        wallet.save()
        
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.TOP_UP,
            amount=amount,
            details=f"Top-up via payment gateway. Order ID: {order_id}"
        )
        messages.success(request, f"Successfully added ₹{amount} to your wallet.")
        return redirect('partner:wallet_details')
    
    messages.info(request, "Payment processed.")
    return redirect('partner:dashboard')

# --- FORGOT PASSWORD LOGIC FOR PARTNERS ---

partner_otp_store = {} 

def partner_reset_password_view(request):
    """Render the single-page reset password flow for partners."""
    return render(request, "partner/reset_password.html")

def partner_ajax_send_otp(request):
    """Step 1: Send OTP to a partner's email """
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        try:
            user = User.objects.get(email=email, partner__isnull=False)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "No partner account found with that email."})
            

        otp = get_random_string(length=6, allowed_chars="0123456789")
        partner_otp_store[user.id] = otp

        send_mail(
            subject="Partner Password Reset OTP",
            message=f"Your OTP for LegalMunshi Partner Portal is: {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        return JsonResponse({"success": True, "message": "OTP sent to your registered email."})
    return JsonResponse({"success": False, "message": "Invalid request method."})

def partner_ajax_verify_otp(request):
    """Step 2: Verify OTP for a partner."""
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        otp_entered = data.get("otp", "").strip()
        try:
             user = User.objects.get(email=email, partner__isnull=False)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "Partner account not found."})

        if partner_otp_store.get(user.id) == otp_entered:
            return JsonResponse({"success": True, "message": "OTP verified."})
        else:
            return JsonResponse({"success": False, "message": "Invalid OTP."})
    return JsonResponse({"success": False, "message": "Invalid request method."})

def partner_ajax_reset_password(request):
    """Step 3: Set new password for a partner."""
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        new_password = data.get("new_password", "").strip()
        try:
            user = User.objects.get(email=email, partner__isnull=False)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "Partner account not found."})

        user.password = make_password(new_password)
        user.save()
        partner_otp_store.pop(user.id, None)
        return JsonResponse({"success": True, "message": "Password updated successfully."})
    return JsonResponse({"success": False, "message": "Invalid request method."})

@login_required
def edit_customer(request, customer_id):
    """
    Handles editing an existing customer's details.
    """
    partner = get_object_or_404(Partner, user=request.user)
    # Security Check: Ensure the customer belongs to the logged-in partner
    customer = get_object_or_404(Customer, id=customer_id, partner=partner)

    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            # Check for email uniqueness if the email has changed
            email = form.cleaned_data['email']
            if Customer.objects.filter(partner=partner, email=email).exclude(id=customer_id).exists():
                messages.error(request, 'Another customer with this email already exists.')
            else:
                form.save()
                messages.success(request, 'Customer details updated successfully!')
                return redirect('partner:customers')
    else:
        # For a GET request, populate the form with the customer's current data
        form = CustomerEditForm(instance=customer)

    return render(request, 'partner/edit_customer.html', {'form': form, 'customer': customer})







@login_required
@require_POST  # Ensures this view only accepts POST requests for security
@transaction.atomic
def delete_customer(request, customer_id):
    """
    Handles the deletion of a customer.
    """
    partner = get_object_or_404(Partner, user=request.user)
    # Security Check: Ensures a partner can only delete their own customers
    customer = get_object_or_404(Customer, id=customer_id, partner=partner)
    
    customer_name = customer.full_name
    customer.delete()
    
    messages.success(request, f"Customer '{customer_name}' was deleted successfully.")
    return redirect('partner:customers')



