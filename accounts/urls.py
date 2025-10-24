# accounts/urls.py

from django.urls import path
from . import views
from .views import login_view, user_signup, verify_otp
from .views import edit_profile

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('my-orders/', views.my_orders, name='orders'),
    path('my-orders/<int:order_id>/', views.order_detail, name='order_detail'),
      # Forgot / Reset Password page (single-page dynamic)
    path("reset-password/", views.reset_password_view, name="reset_password"),

    # AJAX endpoints for single-page flow
    path("ajax/send-otp/", views.ajax_send_otp, name="ajax_send_otp"),
    path("ajax/verify-otp/", views.ajax_verify_otp, name="ajax_verify_otp"),
    path("ajax/reset-password/", views.ajax_reset_password, name="ajax_reset_password"),


]