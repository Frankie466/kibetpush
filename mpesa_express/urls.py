from django.urls import path
from .views import mpesa_stk_push, mpesa_callback, pending_payment
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("", views.home, name="mpesa_home"),  # Add this line for the home page
    path("mpesa/stk_push/", mpesa_stk_push, name="mpesa_stk_push"),
    path("mpesa/callback/", mpesa_callback, name="mpesa_callback"),
    path("payment/pending/", pending_payment, name="pending_payment"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)