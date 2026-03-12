from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse

from .models import Judge


def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_judge_user(user):
    return user.is_authenticated and Judge.objects.filter(user=user).exists()


def get_dashboard_url_for_user(user):
    if is_admin_user(user):
        return reverse("systemadmin:admin_dashboard")
    if is_judge_user(user):
        return reverse("judge:judge_dashboard")
    return reverse("login")


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                reverse("login"),
                REDIRECT_FIELD_NAME,
            )

        if is_admin_user(request.user):
            return view_func(request, *args, **kwargs)

        if is_judge_user(request.user):
            return redirect("judge:judge_dashboard")

        return redirect("login")

    return _wrapped_view


def judge_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                reverse("login"),
                REDIRECT_FIELD_NAME,
            )

        if is_judge_user(request.user):
            return view_func(request, *args, **kwargs)

        if is_admin_user(request.user):
            return redirect("systemadmin:admin_dashboard")

        return redirect("login")

    return _wrapped_view
