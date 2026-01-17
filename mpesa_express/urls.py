from django.urls import path
from .views import mpesa_stk_push, mpesa_callback, pending_payment
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Home page
    path("", views.home, name="mpesa_home"),
    
    # PWA Routes
    path("manifest.json", views.manifest_view, name="manifest"),
    path("serviceworker.js", views.service_worker, name="serviceworker"),
    path("offline/", views.offline_view, name="offline"),
    path('favicon.ico', RedirectView.as_view(url='/static/icons/icon-32x32.png', permanent=True)),
    
    # M-Pesa Payment Routes
    path("mpesa/stk_push/", mpesa_stk_push, name="mpesa_stk_push"),
    path("mpesa/callback/", mpesa_callback, name="mpesa_callback"),
    path("payment/pending/", pending_payment, name="pending_payment"),
]

# Static and media files (for development)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)