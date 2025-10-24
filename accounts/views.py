import random
from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib import messages
from .models import CustomUser
from .forms import UserSignUpForm  # Make sure this form exists
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from .forms import EmailAuthenticationForm
from .forms import EditProfileForm
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, get_user_model
from services.models import ServiceOrder
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Q
from .utils import generate_customer_id,send_otp_email
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist 




User = get_user_model()



def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                try:
                    user.partner
                    messages.error(request, "This is a partner account. Please use the partner login portal.")
                    return redirect('accounts:login') 
                except ObjectDoesNotExist:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.first_name}!")
                    return redirect('home') 
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = EmailAuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def generate_otp():
    return str(random.randint(100000, 999999))


def user_signup(request):
    """
    Handles user signup, stores form data temporarily in session,
    generates and simulates OTP for email .
    """
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)

        if form.is_valid():
            otp = generate_otp()
            

            email = form.cleaned_data['email'].strip()
            phone = form.cleaned_data['phone'].strip()
            password = form.cleaned_data['password1']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            # Check duplicates in CustomUser
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return render(request, 'accounts/signup.html', {'form': form})

            if CustomUser.objects.filter(phone=phone).exists():
                messages.error(request, "Phone number already in use.")
                return render(request, 'accounts/signup.html', {'form': form})

            # Store temporary data in session
            request.session['temp_user_data'] = {
                'email': email,
                'phone': phone,
                'first_name': first_name,
                'last_name': last_name,
                'password1': form.cleaned_data['password1'],
                'password2': form.cleaned_data['password2'],
                'otp': otp,
            }

            # Use the HTML-based email function to send the OTP
            send_otp_email(email, otp, context="Signup")
            messages.success(request, "OTP sent to your Email and Phone.")
            return redirect('accounts:verify_otp')

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserSignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})



def verify_otp(request):
    """
    Verifies OTPs and creates CustomUser upon success.
    """
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        temp_data = request.session.get('temp_user_data')

        if not temp_data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('accounts:signup')

        if otp_input != temp_data['otp']:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'accounts/verify_otp.html')

        # Create CustomUser (with username = email)
        user = CustomUser.objects.create_user(
            email=temp_data['email'],
            phone=temp_data['phone'],
            first_name=temp_data['first_name'],
            last_name=temp_data['last_name'],
            password=temp_data['password1']  # create_user hashes it
        )

         # Generate and assign the unique B2C customer ID
        user.customer_id = generate_customer_id()
        user.save()

        

        login(request, user)
        messages.success(request, "Signup complete! You are now logged in.")

        del request.session['temp_user_data']
        return redirect('home')

    return render(request, 'accounts/verify_otp.html')


def generate_otp():
    return str(random.randint(100000, 999999))

@login_required
def edit_profile(request):
    user = request.user

    # Case 1: POST but OTP not yet submitted (user submitted profile data)
    if request.method == 'POST' and 'otp' not in request.POST:
        form = EditProfileForm(request.POST, instance=user, user=user)
        if form.is_valid():
            # Store changes in session
            request.session['pending_profile_changes'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': form.cleaned_data['email'],
                'phone': form.cleaned_data['phone'],
            }
            # Generate and send OTP
            otp = generate_otp()
            request.session['edit_otp'] = otp
            send_otp_email(user.email, otp, context="Profile Update") # For debug/testing
            messages.info(request, "OTP sent to your email. Please verify to continue.")
            return render(request, 'accounts/verify_otp.html', {
                'action_url': reverse('accounts:edit_profile')
            })
        else:
            # Form invalid, redisplay form with errors
            return render(request, 'accounts/edit_profile.html', {'form': form})

    # Case 2: POST with OTP (user submitting OTP for verification)
    elif request.method == 'POST' and 'otp' in request.POST:
        otp_submitted = request.POST.get('otp')
        otp_saved = request.session.get('edit_otp')

        if otp_submitted == otp_saved:
            # OTP verified, update user profile with session data
            changes = request.session.get('pending_profile_changes')
            if changes:
                for key, value in changes.items():
                    setattr(user, key, value)
                user.save()
                # Clear session data
                request.session.pop('pending_profile_changes', None)
                request.session.pop('edit_otp', None)

                messages.success(request, "Profile updated successfully.")
                return redirect('accounts:edit_profile')
            else:
                messages.error(request, "No changes found to apply.")
                return redirect('accounts:edit_profile')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'accounts/verify_otp.html', {
                'action_url': reverse('accounts:edit_profile')
            })

    # Case 3: GET request, just show form with current user data
    else:
        form = EditProfileForm(instance=user, user=user)
        return render(request, 'accounts/edit_profile.html', {'form': form})


# accounts/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# ✅ Import the required models from your 'services' app
from services.models import ServiceOrder, OrderDocument 

@login_required
def my_orders(request):
    """
    Show all orders placed by the logged-in user.
    Supports optional search by service name.
    """
    # This function is correct. No changes are needed here.
    user = request.user
    orders = ServiceOrder.objects.filter(user=user).order_by('-created_at')
    query = request.GET.get('q', '')
    if query:
        orders = orders.filter(service__title__icontains=query)
    context = {
        'orders': orders,
        'query': query
    }
    return render(request, 'accounts/orders.html', context)

@login_required
def order_detail(request, order_id):
    """
    - Shows order details and previously uploaded documents.
    - Handles new document uploads for the order.
    """
    order = get_object_or_404(ServiceOrder, pk=order_id, user=request.user)

    # This block handles the new document upload when the form is submitted
    if request.method == 'POST':
        new_document_file = request.FILES.get('new_document_file')
        document_name = request.POST.get('document_name')

        if new_document_file and document_name:
            # Create a new document record in the database linked to this order
            OrderDocument.objects.create(
                order=order,
                document_name=document_name,
                file=new_document_file
            )
            messages.success(request, f"Document '{document_name}' uploaded successfully.")
            # Refresh the page to show the newly uploaded document
            return redirect('accounts:order_detail', order_id=order.id)
        else:
            messages.error(request, "Both the file and a document name are required.")

    # This part runs for a normal page load (GET request)
    # The 'order' object is passed to the template, which can then access
    # all related documents using order.uploaded_documents.all
    context = {
        'order': order,
    }
    return render(request, 'accounts/order_detail.html', context)




@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('home')






# --- B2C FORGOT PASSWORD (EMAIL ONLY) ---
User = get_user_model()

# Temporary OTP store (use DB/cache in production)
otp_store = {}


def reset_password_view(request):
    """Render the single-page reset password flow."""
    return render(request, "accounts/reset_password.html")


def _get_json_data(request):
    """Helper to safely parse JSON body."""
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def ajax_send_otp(request):
    """Step 1: Send OTP to email."""
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        try:
            # --- FIX: Logic is now email-only ---
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "No account found with that email."})

        otp = get_random_string(length=6, allowed_chars="0123456789")
        otp_store[user.id] = otp
        send_otp_email(user.email, otp, context="Password Reset")
        return JsonResponse({"success": True, "message": "OTP sent to your registered email."})
    return JsonResponse({"success": False, "message": "Invalid request method."})

def ajax_verify_otp(request):
    """Step 2: Verify OTP."""
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        otp_entered = data.get("otp", "").strip()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "Account not found."})

        if otp_store.get(user.id) == otp_entered:
            return JsonResponse({"success": True, "message": "OTP verified."})
        else:
            return JsonResponse({"success": False, "message": "Invalid OTP."})
    return JsonResponse({"success": False, "message": "Invalid request method."})

def ajax_reset_password(request):
    """Step 3: Set new password."""
    if request.method == "POST":
        data = _get_json_data(request)
        email = data.get("identifier", "").strip()
        new_password = data.get("new_password", "").strip()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "Account not found."})

        user.password = make_password(new_password)
        user.save()
        otp_store.pop(user.id, None)
        return JsonResponse({"success": True, "message": "Password updated successfully."})
    return JsonResponse({"success": False, "message": "Invalid request method."})
