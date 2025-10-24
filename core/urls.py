from django.urls import path
from .views import home_view, placeholder_view
from .views import test_link_view
from .views import about_us_view, contact_us_view
from . import views

urlpatterns = [
    path('', home_view, name='home'),
    path('test/', test_link_view, name='test-link'),
    path('about/', about_us_view, name='about_us'),
    path('contact/', contact_us_view, name='contact_us'),
    path('media-recognition/', views.media_recognition_view, name='media_recognition'),
    path('callback-request/', views.callback_request_page, name='callback_request_page'),
]
