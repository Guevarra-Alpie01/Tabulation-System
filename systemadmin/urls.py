from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = "systemadmin"

urlpatterns = [
    path("admin-dash/", views.admin_dashboard, name="admin_dashboard"),
    path("participants/", views.participant_list, name="participant_list"),
    path("participants/reorder/", views.reorder_participants, name="reorder_participants"),
    path("add-participant/", views.add_participant, name="add_participant"),
    path("participants/<int:participant_id>/edit/", views.edit_participant, name="edit_participant"),
    path("participants/<int:participant_id>/delete/", views.delete_participant, name="delete_participant"),
    path("judges/", views.judge_list, name="judge_list"),
    path("add-judge/", views.add_judge, name="add_judge"),
    path("judges/<int:judge_id>/edit/", views.edit_judge, name="edit_judge"),
    path("judges/<int:judge_id>/delete/", views.delete_judge, name="delete_judge"),
    path("criteria/", views.criteria_list, name="criteria_list"),
    path("criteria/reorder/", views.reorder_criteria, name="reorder_criteria"),
    path("criteria/<int:criteria_id>/go-live/", views.activate_live_criterion, name="activate_live_criterion"),
    path("live/stop/", views.stop_live_criterion, name="stop_live_criterion"),
    path("add-criteria/", views.add_criteria, name="add_criteria"),
    path("criteria/<int:criteria_id>/edit/", views.edit_criteria, name="edit_criteria"),
    path("criteria/<int:criteria_id>/delete/", views.delete_criteria, name="delete_criteria"),
    path("results/", views.tabulation_results, name="tabulation_results"),
    path("results-data/", views.results_data, name="results_data"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
