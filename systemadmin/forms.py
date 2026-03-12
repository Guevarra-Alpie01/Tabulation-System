from django import forms
from .models import Participant, Criteria


class ParticipantForm(forms.ModelForm):

    class Meta:
        model = Participant
        fields = ["name", "photo"]


class CriteriaForm(forms.ModelForm):

    class Meta:
        model = Criteria
        fields = ["name", "percentage"]