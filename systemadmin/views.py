import json
from collections import defaultdict

from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .auth_utils import admin_required
from .forms import CriteriaForm, JudgeAccountForm, ParticipantForm
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


def _normalize_criteria_order():
    criteria = list(Criteria.objects.order_by("display_order", "id"))
    changed = []

    for index, criterion in enumerate(criteria, start=1):
        if criterion.display_order != index:
            criterion.display_order = index
            changed.append(criterion)

    if changed:
        Criteria.objects.bulk_update(changed, ["display_order"])


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


@admin_required
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


@admin_required
def add_participant(request):
    form = ParticipantForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        participant = form.save()
        messages.success(request, f"{participant.name} was added to the tabulation roster.")
        return redirect("systemadmin:participant_list")

    context = _admin_context()
    context["form"] = form
    context["is_edit_mode"] = False
    return render(request, "add_participant.html", context)


@admin_required
def participant_list(request):
    context = _admin_context()
    context["participants"] = Participant.objects.annotate(score_count=Count("score")).order_by("id")
    return render(request, "participant_list.html", context)


@admin_required
def edit_participant(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    form = ParticipantForm(request.POST or None, request.FILES or None, instance=participant)

    if form.is_valid():
        updated_participant = form.save()
        messages.success(request, f"{updated_participant.name} was updated successfully.")
        return redirect("systemadmin:participant_list")

    context = _admin_context()
    context.update(
        {
            "form": form,
            "is_edit_mode": True,
            "participant": participant,
            "linked_score_count": Score.objects.filter(participant=participant).count(),
        }
    )
    return render(request, "add_participant.html", context)


@require_POST
@admin_required
def delete_participant(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    linked_score_count = Score.objects.filter(participant=participant).count()
    participant_name = participant.name
    participant.delete()

    if linked_score_count:
        messages.success(
            request,
            f"{participant_name} was deleted. {linked_score_count} linked score records were also removed.",
        )
    else:
        messages.success(request, f"{participant_name} was deleted successfully.")

    return redirect("systemadmin:participant_list")


@admin_required
def judge_list(request):
    context = _admin_context()
    context["judges"] = Judge.objects.select_related("user").annotate(score_count=Count("score")).order_by("id")
    return render(request, "judge_list.html", context)


@admin_required
def add_judge(request):
    form = JudgeAccountForm(request.POST or None)

    if form.is_valid():
        judge = form.save()
        messages.success(request, f"Judge account {judge.user.username} was created successfully.")
        return redirect("systemadmin:judge_list")

    context = _admin_context()
    context.update(
        {
            "form": form,
            "is_edit_mode": False,
        }
    )
    return render(request, "judge_form.html", context)


@admin_required
def edit_judge(request, judge_id):
    judge = get_object_or_404(Judge.objects.select_related("user"), pk=judge_id)
    form = JudgeAccountForm(request.POST or None, judge=judge)

    if form.is_valid():
        updated_judge = form.save()
        messages.success(request, f"Judge account {updated_judge.user.username} was updated successfully.")
        return redirect("systemadmin:judge_list")

    context = _admin_context()
    context.update(
        {
            "form": form,
            "is_edit_mode": True,
            "judge_account": judge,
            "linked_score_count": Score.objects.filter(judge=judge).count(),
        }
    )
    return render(request, "judge_form.html", context)


@require_POST
@admin_required
def delete_judge(request, judge_id):
    judge = get_object_or_404(Judge.objects.select_related("user"), pk=judge_id)
    linked_score_count = Score.objects.filter(judge=judge).count()
    username = judge.user.username
    judge.user.delete()

    if linked_score_count:
        messages.success(
            request,
            f"Judge account {username} was deleted. {linked_score_count} linked score records were also removed.",
        )
    else:
        messages.success(request, f"Judge account {username} was deleted successfully.")

    return redirect("systemadmin:judge_list")


@admin_required
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


@admin_required
def criteria_list(request):
    context = _admin_context()
    context["criteria"] = Criteria.objects.annotate(score_count=Count("score")).order_by("display_order", "id")
    return render(request, "criteria_list.html", context)


@require_POST
@admin_required
def reorder_criteria(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Invalid request payload."}, status=400)

    ordered_ids = payload.get("ordered_ids")
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return JsonResponse({"success": False, "error": "A full criteria order is required."}, status=400)

    normalized_ids = []
    seen_ids = set()

    for raw_id in ordered_ids:
        try:
            criterion_id = int(raw_id)
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "Criteria order contains an invalid id."}, status=400)

        if criterion_id in seen_ids:
            return JsonResponse({"success": False, "error": "Criteria order contains duplicate ids."}, status=400)

        seen_ids.add(criterion_id)
        normalized_ids.append(criterion_id)

    criteria = list(Criteria.objects.filter(id__in=normalized_ids))
    if len(criteria) != len(normalized_ids) or len(normalized_ids) != Criteria.objects.count():
        return JsonResponse({"success": False, "error": "Criteria order must include every saved criterion."}, status=400)

    criteria_by_id = {criterion.id: criterion for criterion in criteria}
    changed = []

    for index, criterion_id in enumerate(normalized_ids, start=1):
        criterion = criteria_by_id[criterion_id]
        if criterion.display_order != index:
            criterion.display_order = index
            changed.append(criterion)

    if changed:
        Criteria.objects.bulk_update(changed, ["display_order"])

    return JsonResponse({"success": True})


@admin_required
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
@admin_required
def delete_criteria(request, criteria_id):
    criterion = get_object_or_404(Criteria, pk=criteria_id)
    linked_score_count = Score.objects.filter(criteria=criterion).count()
    criterion_name = criterion.name
    criterion.delete()
    _normalize_criteria_order()

    if linked_score_count:
        messages.success(
            request,
            f"{criterion_name} criteria was deleted. {linked_score_count} linked score records were also removed.",
        )
    else:
        messages.success(request, f"{criterion_name} criteria was deleted successfully.")

    return redirect("systemadmin:criteria_list")


@admin_required
def tabulation_results(request):
    context = _admin_context()
    context.update(
        {
            "results": _calculate_results(),
            "has_scores": Score.objects.exists(),
        }
    )
    return render(request, "results.html", context)


@admin_required
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
