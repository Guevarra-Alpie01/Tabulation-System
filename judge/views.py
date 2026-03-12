from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from systemadmin.auth_utils import judge_required
from systemadmin.models import (
    Criteria,
    Judge,
    LiveCriteriaSession,
    LiveCriteriaSubmission,
    Participant,
    Score,
)
from systemadmin.scoring_utils import acquire_scoring_write_lock


def _get_active_live_session():
    return (
        LiveCriteriaSession.objects.filter(is_active=True)
        .select_related("criterion")
        .order_by("-activated_at", "-id")
        .first()
    )


def _build_live_score_rows(judge, active_session, posted_scores=None, participants=None):
    if participants is None:
        participants = list(Participant.objects.only("id", "name", "photo", "display_order").order_by("display_order", "id"))
    existing_scores = {}

    if active_session:
        existing_scores = {
            score.participant_id: score.score_value
            for score in Score.objects.filter(judge=judge, criteria=active_session.criterion)
        }

    rows = []
    for participant in participants:
        score_value = ""
        if posted_scores and participant.id in posted_scores:
            score_value = posted_scores[participant.id]
        elif participant.id in existing_scores:
            score_value = existing_scores[participant.id]

        rows.append(
            {
                "participant": participant,
                "candidate_number": participant.display_order,
                "score_value": score_value,
            }
        )

    return rows


def _build_dashboard_context(judge, posted_scores=None):
    active_live_session = _get_active_live_session()
    live_submission = None
    live_score_rows = []
    participants = []

    if active_live_session:
        participants = list(Participant.objects.only("id", "name", "photo", "display_order").order_by("display_order", "id"))
        live_submission = (
            LiveCriteriaSubmission.objects.filter(session=active_live_session, judge=judge)
            .order_by("-submitted_at")
            .first()
        )
        live_score_rows = _build_live_score_rows(
            judge,
            active_live_session,
            posted_scores=posted_scores,
            participants=participants,
        )

    return {
        "participants": participants,
        "judge": judge,
        "active_live_session": active_live_session,
        "live_submission": live_submission,
        "live_score_rows": live_score_rows,
        "focus_live_mode": bool(active_live_session),
    }


def _parse_whole_number_score(raw_value, label):
    normalized_value = str(raw_value).strip()
    if not normalized_value:
        raise ValueError(f"Enter a score for {label}.")

    try:
        score_value = int(normalized_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must have a whole number score.") from exc

    if not 1 <= score_value <= 100:
        raise ValueError(f"{label} must be scored from 1 to 100.")

    return score_value


@judge_required
def judge_dashboard(request):
    judge = Judge.objects.select_related("user").get(user=request.user)
    return render(request, "dashboard.html", _build_dashboard_context(judge))


@require_POST
@judge_required
@transaction.atomic
def submit_live_scores(request):
    judge = Judge.objects.select_related("user").get(user=request.user)
    acquire_scoring_write_lock()
    active_live_session = _get_active_live_session()

    if not active_live_session:
        messages.error(request, "There is no live judging criterion at the moment.")
        return redirect("judge:judge_dashboard")

    submitted_session_id = str(request.POST.get("live_session_id", "")).strip()
    if submitted_session_id != str(active_live_session.id):
        messages.error(request, "The live criterion changed while you were scoring. Review the current live criterion and submit again.")
        return redirect("judge:judge_dashboard")

    if LiveCriteriaSubmission.objects.filter(session=active_live_session, judge=judge).exists():
        messages.info(request, f"You already submitted scores for {active_live_session.criterion.name}.")
        return redirect("judge:judge_dashboard")

    participants = list(Participant.objects.only("id", "name", "photo", "display_order").order_by("display_order", "id"))
    if not participants:
        messages.error(request, "No participants are available for live scoring.")
        return redirect("judge:judge_dashboard")

    posted_scores = {}
    validation_errors = []
    parsed_scores = {}

    for participant in participants:
        field_name = f"participant_{participant.id}"
        raw_value = str(request.POST.get(field_name, "")).strip()
        posted_scores[participant.id] = raw_value

        try:
            parsed_scores[participant.id] = _parse_whole_number_score(raw_value, participant.name)
        except ValueError as exc:
            validation_errors.append(str(exc))

    if validation_errors:
        context = _build_dashboard_context(judge, posted_scores=posted_scores)
        context["live_submission_error"] = validation_errors[0]
        return render(request, "dashboard.html", context, status=400)

    existing_scores = {
        score.participant_id: score
        for score in Score.objects.filter(
            judge=judge,
            criteria=active_live_session.criterion,
            participant__in=participants,
        )
    }
    scores_to_create = []
    scores_to_update = []

    for participant in participants:
        score_value = parsed_scores[participant.id]
        existing_score = existing_scores.get(participant.id)

        if existing_score:
            if existing_score.score_value != score_value:
                existing_score.score_value = score_value
                scores_to_update.append(existing_score)
            continue

        scores_to_create.append(
            Score(
                judge=judge,
                participant=participant,
                criteria=active_live_session.criterion,
                score_value=score_value,
            )
        )

    if scores_to_update:
        Score.objects.bulk_update(scores_to_update, ["score_value"])
    if scores_to_create:
        Score.objects.bulk_create(scores_to_create)

    submission, created = LiveCriteriaSubmission.objects.get_or_create(session=active_live_session, judge=judge)
    if not created:
        messages.info(request, f"You already submitted scores for {active_live_session.criterion.name}.")
        return redirect("judge:judge_dashboard")

    messages.success(
        request,
        f"Your {active_live_session.criterion.name} scores were submitted for all participants.",
    )
    return redirect("judge:judge_dashboard")


@judge_required
def live_status(request):
    judge = Judge.objects.only("id").get(user=request.user)
    active_live_session = _get_active_live_session()
    judge_has_submitted = False

    if active_live_session:
        judge_has_submitted = LiveCriteriaSubmission.objects.filter(
            session=active_live_session,
            judge=judge,
        ).exists()

    return JsonResponse(
        {
            "active_session_id": active_live_session.id if active_live_session else None,
            "criterion_name": active_live_session.criterion.name if active_live_session else "",
            "judge_has_submitted": judge_has_submitted,
        }
    )


@judge_required
def score_participant(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    criteria_list = list(Criteria.objects.only("id", "name", "percentage", "display_order").order_by("display_order", "id"))
    judge = Judge.objects.select_related("user").get(user=request.user)

    if request.method == "POST":
        validation_errors = []
        parsed_scores = {}

        for criteria in criteria_list:
            try:
                parsed_scores[criteria.id] = _parse_whole_number_score(
                    request.POST.get(f"criteria_{criteria.id}", ""),
                    criteria.name,
                )
            except ValueError as exc:
                validation_errors.append(str(exc))

        if validation_errors:
            messages.error(request, validation_errors[0])
            return render(
                request,
                "score_participant.html",
                {
                    "participant": participant,
                    "criteria_list": criteria_list,
                    "judge": judge,
                },
                status=400,
            )

        with transaction.atomic():
            acquire_scoring_write_lock()
            existing_scores = {
                score.criteria_id: score
                for score in Score.objects.filter(
                    judge=judge,
                    participant=participant,
                    criteria__in=criteria_list,
                )
            }
            scores_to_create = []
            scores_to_update = []

            for criteria in criteria_list:
                score_value = parsed_scores[criteria.id]
                existing_score = existing_scores.get(criteria.id)

                if existing_score:
                    if existing_score.score_value != score_value:
                        existing_score.score_value = score_value
                        scores_to_update.append(existing_score)
                    continue

                scores_to_create.append(
                    Score(
                        judge=judge,
                        participant=participant,
                        criteria=criteria,
                        score_value=score_value,
                    )
                )

            if scores_to_update:
                Score.objects.bulk_update(scores_to_update, ["score_value"])
            if scores_to_create:
                Score.objects.bulk_create(scores_to_create)

        messages.success(request, f"Scores for {participant.name} were saved successfully.")
        return redirect("judge:judge_dashboard")

    return render(
        request,
        "score_participant.html",
        {
            "participant": participant,
            "criteria_list": criteria_list,
            "judge": judge,
        },
    )
