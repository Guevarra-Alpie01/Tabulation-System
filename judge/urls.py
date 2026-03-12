from django.urls import path

from . import views
from django .conf import settings
from django.conf.urls.static import static

app_name = 'judge'

urlpatterns = [
    path("", views.judge_dashboard, name="judge_dashboard"),
    path("score/<int:participant_id>/",views.score_participant,name="score_participant"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

