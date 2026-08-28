from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('rides.dashboard_urls')),
    path('dashboard/', include('content.dashboard_urls')),

    # Public blog & gallery — declared before the rides catch-all at ''
    path('', include('content.urls')),

    path('', include('rides.urls')),
]

# Serve uploaded media through Django. This is slower than letting the web
# server do it, but the shared host this deploys to has no per-path config, so
# the alternative is broken images. Point Apache/Nginx at MEDIA_ROOT and delete
# this block if that ever becomes an option.
urlpatterns += [
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]
