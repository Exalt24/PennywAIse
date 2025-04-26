from django.contrib import admin
from django.urls import include, path
from debug_toolbar.toolbar import debug_toolbar_urls
from mysite import settings

urlpatterns = [
    path('', include('budget.urls')),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]

if not settings.TESTING:
    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()