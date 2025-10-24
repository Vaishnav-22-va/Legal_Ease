from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # Universal payment page
    path("payment/", views.payment_page, name="payment_page"),

    # Generic success and failure pages, useful for routing from gateways
    path("success/<str:order_id>/", views.payment_success, name="success"),
    path("service/failed/<str:order_id>/", views.service_payment_failed, name="service_failed"),
    path('success/<str:order_id>/', views.payment_success, name='payment_success'),
    

    # Service-specific URLs
    path("service/checkout/", views.service_payment_page, name="service_checkout"),
    path("service/success/<str:order_id>/", views.service_payment_success, name="service_success"),
    path("service/failed/", views.service_payment_failed, name="service_failed"),
]
