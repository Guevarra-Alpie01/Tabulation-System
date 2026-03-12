from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = "judge"

urlpatterns = [
    path("", views.judge_dashboard, name="judge_dashboard"),
    path("live/submit/", views.submit_live_scores, name="submit_live_scores"),
    path("live/status/", views.live_status, name="live_status"),
    path("score/<int:participant_id>/", views.score_participant, name="score_participant"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
