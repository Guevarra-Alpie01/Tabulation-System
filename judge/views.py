from django.http import HttpResponse
from django.shortcuts import render,redirect,get_object_or_404

from django.contrib.auth.decorators import login_required

from systemadmin.models import Participant, Criteria, Score, Judge

def judge_dashboard(request):

    participants = Participant.objects.all()

    return render(request, "dashboard.html", {
        "participants": participants
    })

@login_required
def score_participant(request, participant_id):

    participant = get_object_or_404(Participant, id=participant_id)

    criteria_list = Criteria.objects.all()

    judge = Judge.objects.get(user=request.user)

    if request.method == "POST":

        for c in criteria_list:

            score_value = request.POST.get(f"criteria_{c.id}")

            Score.objects.update_or_create(
                judge=judge,
                participant=participant,
                criteria=c,
                defaults={"score_value": score_value}
            )

        return redirect("judge_dashboard")

    return render(request, "score_participant.html", {
        "participant": participant,
        "criteria_list": criteria_list
    })
