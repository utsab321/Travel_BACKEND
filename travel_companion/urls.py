from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

def api_root(request):
    return JsonResponse({
        "message": "Travel API is running"
    })
# Import after django.conf is ready
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_companion.settings')

# Patch the admin site
from core.admin import patch_admin_site
patch_admin_site()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root),
    path('api/users/', include('apps.users.urls')),
    path('api/trips/', include('apps.trips.urls')),
    path('api/trips/expenses/', include('apps.expenses.urls')),
    path('api/chat/', include('apps.chat.urls_new')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('core.urls')),  # Stats and public stats dashboard
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)