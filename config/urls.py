from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('members/', include('apps.members.urls')),
    path('vehicles/', include('apps.vehicles.urls')),
    path('qualifications/', include('apps.qualifications.urls')),
    path('scheduling/', include('apps.scheduling.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
