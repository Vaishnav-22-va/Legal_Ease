# services/urls.py

from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    # Core service browsing URLs
    path('', views.service_list, name='list'),
    path('<slug:slug>/', views.service_info, name='info'),

    # The unified URL for applying for a service
    path('<slug:slug>/apply/', views.service_order_create, name='apply'),
    
    # --- NEW, CORRECT PAYMENT FLOW URLs ---
    # This page displays the smart payment options (Wallet vs. Gateway)
    path('order/<int:order_id>/checkout/', views.service_checkout, name='checkout'),
    
    # This URL handles the form submission to process the payment
    path('order/<int:order_id>/process-payment/', views.process_service_payment, name='process_payment'),
    path('admin/service-order-chart/', views.service_order_chart, name='service_order_chart_json'),
]