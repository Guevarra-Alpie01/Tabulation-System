from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from systemadmin.auth_utils import get_dashboard_url_for_user, is_admin_user, is_judge_user
from systemadmin.forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_user(request.user))

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.username}.")

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            if is_admin_user(user) and next_url.startswith("/sys-admin/"):
                return redirect(next_url)
            if is_judge_user(user) and next_url.startswith("/judge/"):
                return redirect(next_url)

        return redirect(get_dashboard_url_for_user(user))

    return render(
        request,
        "login.html",
        {
            "form": form,
            "next": request.GET.get("next", ""),
        },
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")

    return redirect("login")
