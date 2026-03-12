from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db.models import Sum

from .models import Criteria, Judge, Participant


User = get_user_model()


def _apply_form_input_style(fields):
    for field in fields.values():
        existing_class = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (existing_class + " form-input").strip()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_input_style(self.fields)


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ["name", "photo"]
        labels = {
            "name": "Participant Name",
            "photo": "Profile Photo",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Enter the participant's display name",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "accept": "image/*",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_input_style(self.fields)


class CriteriaForm(forms.ModelForm):
    class Meta:
        model = Criteria
        fields = ["name", "percentage"]
        labels = {
            "name": "Criteria Name",
            "percentage": "Percentage Weight",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Example: Stage Presence",
                }
            ),
            "percentage": forms.NumberInput(
                attrs={
                    "placeholder": "0 - 100",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_form_input_style(self.fields)

    def clean_percentage(self):
        percentage = self.cleaned_data["percentage"]

        if percentage <= 0:
            raise ValidationError("The criterion weight must be greater than 0%.")

        if percentage > 100:
            raise ValidationError("The criterion weight cannot be greater than 100%.")

        return percentage

    def clean(self):
        cleaned_data = super().clean()
        percentage = cleaned_data.get("percentage")

        if percentage is None:
            return cleaned_data

        existing_total = (
            Criteria.objects.exclude(pk=self.instance.pk).aggregate(total=Sum("percentage"))["total"] or 0
        )
        projected_total = round(existing_total + percentage, 2)

        if projected_total > 100.01:
            raise ValidationError(
                f"The total criteria weight cannot exceed 100%. This update would raise the total to {projected_total:.2f}%."
            )

        return cleaned_data


class JudgeAccountForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Judge Username",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter a judge username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.judge = kwargs.pop("judge", None)
        super().__init__(*args, **kwargs)
        _apply_form_input_style(self.fields)

        if self.judge:
            self.fields["username"].initial = self.judge.user.username
            self.fields["password"].help_text = "Leave blank to keep the current password."
            self.fields["confirm_password"].help_text = "Leave blank to keep the current password."
            self.fields["password"].widget.attrs["placeholder"] = "Leave blank to keep current password"
            self.fields["confirm_password"].widget.attrs["placeholder"] = "Repeat new password if changing"

    def clean_username(self):
        username = self.cleaned_data["username"]
        queryset = User.objects.filter(username=username)
        if self.judge:
            queryset = queryset.exclude(pk=self.judge.user_id)

        if queryset.exists():
            raise ValidationError("This username is already in use.")

        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if self.judge:
            if password or confirm_password:
                if not password or not confirm_password:
                    raise ValidationError("Enter the new password in both password fields.")
                if password != confirm_password:
                    raise ValidationError("The password fields do not match.")
        else:
            if not password or not confirm_password:
                raise ValidationError("Username and password are required to create a judge account.")
            if password != confirm_password:
                raise ValidationError("The password fields do not match.")

        return cleaned_data

    def save(self):
        username = self.cleaned_data["username"]
        password = self.cleaned_data.get("password")

        if self.judge:
            user = self.judge.user
        else:
            user = User()

        user.username = username
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True

        if password:
            user.set_password(password)
        elif not user.pk:
            raise ValidationError("A password is required to create a judge account.")

        user.save()

        if self.judge:
            return self.judge

        return Judge.objects.create(user=user)
