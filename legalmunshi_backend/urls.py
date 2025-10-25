# legalmunshi_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from core.views import home_view
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "Legal Munshi"
admin.site.site_title = "My Custom Admin Portal"
admin.site.index_title = "Welcome to the Dashboard"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('', home_view, name='home'),
    path('', include('core.urls')),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('services/', include('services.urls', namespace='services')),
    path('admin-panel/', include(('admin_panel.urls', 'admin_panel'), namespace='admin_panel')),
    path("payment/", include(("payments.urls", "payments"), namespace="payments")),
    path('partner/', include('partner.urls', namespace='partner')),
    path('', include(('core.urls', 'core'), namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)