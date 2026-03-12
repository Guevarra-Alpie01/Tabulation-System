from django.urls import path

from . import views
from django .conf import settings
from django.conf.urls.static import static

app_name = 'systemadmin'

urlpatterns = [
    path("admin-dash/", views.admin_dashboard, name="admin_dashboard"),

    path("participants/", views.participant_list, name="participant_list"),
    path("add-participant/", views.add_participant, name="add_participant"),

    path("criteria/", views.criteria_list, name="criteria_list"),
    path("add-criteria/", views.add_criteria, name="add_criteria"),
    path("criteria/<int:criteria_id>/edit/", views.edit_criteria, name="edit_criteria"),
    path("criteria/<int:criteria_id>/delete/", views.delete_criteria, name="delete_criteria"),

    path("results/", views.tabulation_results, name="tabulation_results"),
    path("results-data/", views.results_data, name="results_data"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
