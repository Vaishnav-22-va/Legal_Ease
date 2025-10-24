from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from services.models import ServiceOrder
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from services.models import ServiceCategory



def custom_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff:  # allow only staff to login to admin panel
                login(request, user)
                return redirect("admin_panel:dashboard")
            else:
                messages.error(request, "You do not have permission to access the admin panel.")
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, "admin_panel/login.html")

@login_required(login_url="admin_panel:login")
@user_passes_test(lambda u: u.is_staff, login_url="admin_panel:login")
def dashboard(request):
    # You can add your stats logic here
    return render(request, "admin_panel/dashboard.html")

def custom_logout(request):
    logout(request)
    return redirect("admin_panel:login")

def staff_required(view_func):
    @login_required
    @user_passes_test(lambda u: u.is_staff)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@staff_required
def dashboard(request):
    total_orders = ServiceOrder.objects.count()
    pending_orders = ServiceOrder.objects.filter(status='pending').count()
    completed_orders = ServiceOrder.objects.filter(status='paid').count()
    rejected_orders = ServiceOrder.objects.filter(status='cancelled').count()
    
    # Only sum sales of paid orders
    total_sales = ServiceOrder.objects.filter(status='paid').aggregate(
        total=Sum('service__price_user')
    )['total'] or 0

    recent_orders = ServiceOrder.objects.select_related('service', 'user').order_by('-created_at')[:5]

    context = {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "rejected_orders": rejected_orders,
        "total_sales": total_sales,
        "recent_orders": recent_orders,
    }
    return render(request, "admin_panel/dashboard.html", context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from services.models import ServiceOrder  # Adjust import based on your models

def staff_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_staff)(view_func))

@staff_required
def order_management(request):
    orders = ServiceOrder.objects.select_related('service', 'user').order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'admin_panel/order_management.html', context)



@login_required(login_url='admin_panel:login')
@user_passes_test(lambda u: u.is_staff, login_url='admin_panel:login')
def service_category_list(request):
    categories = ServiceCategory.objects.all()
    return render(request, 'admin_panel/service_list.html', {'categories': categories})

@login_required(login_url='admin_panel:login')
@user_passes_test(lambda u: u.is_staff, login_url='admin_panel:login')
def service_list(request):
    # Fetch your Service objects here once the model is ready
    return render(request, 'admin_panel/service_list.html', {})