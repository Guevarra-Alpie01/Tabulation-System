from django.shortcuts import get_object_or_404, redirect, render

from systemadmin.auth_utils import judge_required
from systemadmin.models import Criteria, Judge, Participant, Score


@judge_required
def judge_dashboard(request):
    participants = Participant.objects.all()
    judge = Judge.objects.get(user=request.user)

    return render(
        request,
        "dashboard.html",
        {
            "participants": participants,
            "judge": judge,
        },
    )


@judge_required
def score_participant(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    criteria_list = Criteria.objects.order_by("display_order", "id")
    judge = Judge.objects.get(user=request.user)

    if request.method == "POST":
        for criteria in criteria_list:
            score_value = request.POST.get(f"criteria_{criteria.id}")

            Score.objects.update_or_create(
                judge=judge,
                participant=participant,
                criteria=criteria,
                defaults={"score_value": score_value},
            )

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
