from django.urls import path
from .views import (
    nestlink_payment, 
    nestlink_callback, 
    pending_payment,
    check_payment_status,
    manifest_view,
    service_worker,
    offline_view,
    home
)
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Home page
    path("", home, name="home"),
    
    # PWA Routes
    path("manifest.json", manifest_view, name="manifest"),
    path("serviceworker.js", service_worker, name="serviceworker"),
    path("offline/", offline_view, name="offline"),
    path('favicon.ico', RedirectView.as_view(url='/static/icons/icon-32x32.png', permanent=True)),
    
    # M-Pesa Payment Routes (Keep for backward compatibility if needed)
    # path("mpesa/stk_push/", mpesa_stk_push, name="mpesa_stk_push"),
    # path("mpesa/callback/", mpesa_callback, name="mpesa_callback"),
    
    # Nestlink Payment Routes
    path("nestlink/payment/", nestlink_payment, name="nestlink_payment"),
    path("nestlink/callback/", nestlink_callback, name="nestlink_callback"),
    path("nestlink/check-status/", check_payment_status, name="check_payment_status"),
    
    # Payment Status Page
    path("payment/pending/", pending_payment, name="pending_payment"),
]

# Static and media files (for development)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)