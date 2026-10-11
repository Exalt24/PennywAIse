from django.contrib import admin
from django.urls import include, path
from mysite import settings
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', include('budget.urls')),
    path("admin/", admin.site.urls),
    path('logout/', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path("__reload__/", include("django_browser_reload.urls")),
]

if not settings.TESTING:
    # imported here because debug_toolbar is not in INSTALLED_APPS while testing
    from debug_toolbar.toolbar import debug_toolbar_urls
    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()