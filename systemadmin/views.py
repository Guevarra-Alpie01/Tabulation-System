from collections import defaultdict

from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CriteriaForm, ParticipantForm
from .models import Criteria, Judge, Participant, Score


def _calculate_results():
    participants = list(Participant.objects.all())
    scores_by_participant = defaultdict(list)

    for score in Score.objects.select_related("criteria", "participant"):
        scores_by_participant[score.participant_id].append(score)

    results = []
    for participant in participants:
        total = 0
        participant_scores = scores_by_participant.get(participant.id, [])

        for score in participant_scores:
            total += (score.score_value / 100) * score.criteria.percentage

        results.append(
            {
                "participant": participant,
                "score": round(total, 2),
                "criteria_scored": len(participant_scores),
            }
        )

    return sorted(results, key=lambda item: item["score"], reverse=True)


def _admin_context():
    participant_count = Participant.objects.count()
    criteria_count = Criteria.objects.count()
    judge_count = Judge.objects.count()
    score_count = Score.objects.count()
    criteria_total = round(
        Criteria.objects.aggregate(total=Sum("percentage"))["total"] or 0,
        2,
    )

    return {
        "admin_summary": {
            "participant_count": participant_count,
            "criteria_count": criteria_count,
            "judge_count": judge_count,
            "score_count": score_count,
            "criteria_total": criteria_total,
            "criteria_ready": criteria_count > 0 and abs(criteria_total - 100) < 0.01,
        }
    }


def admin_dashboard(request):
    results = _calculate_results()
    context = _admin_context()
    context.update(
        {
            "top_results": results[:5],
            "has_scores": Score.objects.exists(),
        }
    )
    return render(request, "admin_dashboard.html", context)


def add_participant(request):
    form = ParticipantForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        participant = form.save()
        messages.success(request, f"{participant.name} was added to the tabulation roster.")
        return redirect("systemadmin:participant_list")

    context = _admin_context()
    context["form"] = form
    return render(request, "add_participant.html", context)


def participant_list(request):
    context = _admin_context()
    context["participants"] = Participant.objects.all()
    return render(request, "participant_list.html", context)


def add_criteria(request):
    form = CriteriaForm(request.POST or None)

    if form.is_valid():
        criteria = form.save()
        messages.success(request, f"{criteria.name} criteria was added successfully.")
        return redirect("systemadmin:criteria_list")

    context = _admin_context()
    context["form"] = form
    context["is_edit_mode"] = False
    return render(request, "add_criteria.html", context)


def criteria_list(request):
    context = _admin_context()
    context["criteria"] = Criteria.objects.annotate(score_count=Count("score")).order_by("id")
    return render(request, "criteria_list.html", context)


def edit_criteria(request, criteria_id):
    criterion = get_object_or_404(Criteria, pk=criteria_id)
    form = CriteriaForm(request.POST or None, instance=criterion)

    if form.is_valid():
        updated_criterion = form.save()
        messages.success(request, f"{updated_criterion.name} criteria was updated successfully.")
        return redirect("systemadmin:criteria_list")

    context = _admin_context()
    context.update(
        {
            "form": form,
            "is_edit_mode": True,
            "criterion": criterion,
            "linked_score_count": Score.objects.filter(criteria=criterion).count(),
        }
    )
    return render(request, "add_criteria.html", context)


@require_POST
def delete_criteria(request, criteria_id):
    criterion = get_object_or_404(Criteria, pk=criteria_id)
    linked_score_count = Score.objects.filter(criteria=criterion).count()
    criterion_name = criterion.name
    criterion.delete()

    if linked_score_count:
        messages.success(
            request,
            f"{criterion_name} criteria was deleted. {linked_score_count} linked score records were also removed.",
        )
    else:
        messages.success(request, f"{criterion_name} criteria was deleted successfully.")

    return redirect("systemadmin:criteria_list")


def tabulation_results(request):
    context = _admin_context()
    context.update(
        {
            "results": _calculate_results(),
            "has_scores": Score.objects.exists(),
        }
    )
    return render(request, "results.html", context)


def results_data(request):
    results = []

    for item in _calculate_results():
        participant = item["participant"]
        results.append(
            {
                "name": participant.name,
                "photo_url": participant.photo.url if participant.photo else "",
                "score": item["score"],
                "criteria_scored": item["criteria_scored"],
            }
        )

    return JsonResponse({"results": results})
