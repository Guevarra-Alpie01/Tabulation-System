from django import forms

class ScoreInputForm(forms.Form):

    score = forms.IntegerField(
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Enter score (1-100)"
        })
    )