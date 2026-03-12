from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("judge/", include("judge.urls")),
    path("sys-admin/", include("systemadmin.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
