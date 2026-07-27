"""
Root URL configuration for ai_assistant project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from django.views.generic import TemplateView

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # JWT token refresh
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Core API
    path('api/', include('core.urls')),

    # SPA catch-all — serve the frontend
    path('', TemplateView.as_view(template_name='core/index.html'), name='spa'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
