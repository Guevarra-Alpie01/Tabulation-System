from django.db import models
from django.contrib.auth.models import User


class Criteria(models.Model):
    name = models.CharField(max_length=100)
    percentage = models.FloatField()

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"


class Participant(models.Model):
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)

    def __str__(self):
        return self.name

    def final_score(self):
        scores = Score.objects.filter(participant=self)

        total = 0
        for s in scores:
            total += (s.score_value / 100) * s.criteria.percentage

        return round(total, 2)


class Judge(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class Score(models.Model):

    judge = models.ForeignKey(Judge, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    criteria = models.ForeignKey(Criteria, on_delete=models.CASCADE)

    score_value = models.IntegerField()

    class Meta:
        unique_together = ("judge", "participant", "criteria")

    def weighted_score(self):
        return (self.score_value / 100) * self.criteria.percentage