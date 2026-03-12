from django.shortcuts import render, redirect, get_object_or_404
from .models import Participant, Criteria, Score, Judge
from .forms import ParticipantForm, CriteriaForm
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import User

from django.db.models import Avg


def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

def add_participant(request):

    form = ParticipantForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        return redirect("systemadmin:participant_list")

    return render(request, "add_participant.html", {
        "form": form
    })

def participant_list(request):

    participants = Participant.objects.all()

    return render(request, "participant_list.html", {
        "participants": participants
    })

def add_criteria(request):

    form = CriteriaForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("systemadmin:criteria_list")

    return render(request, "add_criteria.html", {
        "form": form
    })

def criteria_list(request):

    criteria = Criteria.objects.all()

    return render(request, "criteria_list.html", {
        "criteria": criteria
    })

def tabulation_results(request):

    participants = Participant.objects.all()

    results = []

    for p in participants:

        scores = Score.objects.filter(participant=p)

        total = 0
        for s in scores:
            total += (s.score_value / 100) * s.criteria.percentage

        results.append({
            "participant": p,
            "score": round(total, 2)
        })

    # automatic ranking
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return render(request, "results.html", {
        "results": results
    })

from django.http import JsonResponse


def results_data(request):

    participants = Participant.objects.all()

    results = []

    for p in participants:

        scores = Score.objects.filter(participant=p)

        total = 0
        for s in scores:
            total += (s.score_value / 100) * s.criteria.percentage

        results.append({
            "name": p.name,
            "score": round(total,2)
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return JsonResponse({"results": results})