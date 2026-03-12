from django import forms
from .models import Participant, Criteria


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
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing_class + " form-input").strip()


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
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing_class + " form-input").strip()
