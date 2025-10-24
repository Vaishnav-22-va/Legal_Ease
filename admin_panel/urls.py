from django.urls import path
from . import views

app_name = 'admin_panel'  # Add this line to register the namespace

urlpatterns = [

    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("orders/", views.order_management, name="order_management"),

    # 👇 This is the correct route for service categories management
    path("service-categories/", views.service_category_list, name="service_category_list"),
     path('services/', views.service_list, name='service_list'),
]


