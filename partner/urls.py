# partners/urls.py

from django.urls import path
from . import views

app_name = 'partner'

urlpatterns = [
    # --- Signup, Auth, and Payment Flow ---
    path('signup/', views.partner_signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('waiting-for-approval/', views.waiting_for_approval_view, name='waiting_for_approval'),
    
    # AJAX endpoints for the signup form
    path('api/check-existence/', views.check_partner_existence, name='check_existence'),
    path('api/send-otp/', views.ajax_send_otp, name='send_otp'),
    path('api/verify-otp/', views.ajax_verify_otp, name='verify_otp'),
    path('api/signup-submit/', views.ajax_signup_submit, name='signup_submit'),

    # Payment callback (expects order_id as a query parameter)
    path('payment-callback/', views.partner_payment_callback, name='payment_callback'),
    path('payment-success/', views.payment_success_callback, name='payment_success'),


    # --- Partner Dashboard ---
    path('dashboard/', views.partner_dashboard, name='dashboard'),

    
    # --- Wallet Management ---
    path('my-plan/', views.my_plan_details, name='my_plan'), 
    path('upgrade-plan/', views.upgrade_plan, name='upgrade_plan'), 
    path('wallet/', views.wallet_details, name='wallet_details'),
    path('wallet/top-up/', views.top_up_wallet, name='wallet_top_up'),

    # --- Order Management ---
    path("orders/", views.partner_orders, name="orders"),
    path("orders/<int:order_id>/", views.partner_order_detail, name="order_detail"),

    
    # --- Customer Management ---
    path("customers/", views.partner_customers, name="customers"),
    path("create-order/select-customer/", views.select_customer_for_order, name="select_customer_for_order"),
    path('customers/edit/<int:customer_id>/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),

    # --- FORGOT PASSWORD URLS ---
    path("reset-password/", views.partner_reset_password_view, name="reset_password"),

     # AJAX endpoints for the single-page flow
    path("ajax/send-otp/", views.partner_ajax_send_otp, name="ajax_send_otp"),
    path("ajax/verify-otp/", views.partner_ajax_verify_otp, name="ajax_verify_otp"),
    path("ajax/reset-password/", views.partner_ajax_reset_password, name="ajax_reset_password"),
]

