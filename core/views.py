# core/views.py

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.forms import EditProfileForm
from services.models import ServiceCategory, Service
from django.urls import path
from . import views
from .models import CallbackRequest


def home_view(request):
    featured_services = Service.objects.filter(is_featured=True, is_active=True).order_by('title')[:20]
    all_services = Service.objects.filter(is_active=True).order_by('title')
    context = {
        'featured_services': featured_services,
        'all_services': all_services,
        # 'navbar_categories' ko hata do yaha
    }
    return render(request, 'core/index.html', context)




# Temporary placeholder for under-construction views
def placeholder_view(request):
    return HttpResponse("<h1>This page is under construction</h1>")


def test_link_view(request):
    return render(request, 'core/test_link.html')

def about_us_view(request):
    return render(request, 'core/about_us.html')

def contact_us_view(request):
    return render(request, 'core/contact_us.html')

# your_project/core/views.py

from django.shortcuts import render
from .models import MediaCategory, MediaItem

def media_recognition_view(request):
    # Get all categories and their related items
    categories = MediaCategory.objects.all().prefetch_related('media_items')

    # Get the highlighted items
    highlighted_items = MediaItem.objects.filter(is_highlighted=True)

    context = {
        'highlighted_items': highlighted_items,
        'categories': categories,
    }
    return render(request, 'core/media_recognition.html', context)

def callback_request_page(request):
    if request.method == 'POST':
        # Extract form data and create object in one call
        CallbackRequest.objects.create(
            name=request.POST.get('name'),
            mobile_no=request.POST.get('mobile_no'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message')
        )
        
        messages.success(request, "Thank you for your request! We will contact you soon.")
        return redirect('callback_request_page')
    return render(request, 'core/callback_request.html')

