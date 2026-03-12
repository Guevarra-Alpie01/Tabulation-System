from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg, Max


class Criteria(models.Model):
    name = models.CharField(max_length=100)
    percentage = models.FloatField()
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.display_order:
            max_order = type(self).objects.aggregate(max_order=Max("display_order"))["max_order"] or 0
            self.display_order = max_order + 1

        super().save(*args, **kwargs)


class Participant(models.Model):
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to="participants/", blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.name

    def final_score(self):
        averaged_scores = (
            Score.objects.filter(participant=self)
            .values("criteria_id", "criteria__percentage")
            .annotate(avg_score=Avg("score_value"))
        )

        total = 0
        for averaged_score in averaged_scores:
            total += (averaged_score["avg_score"] / 100) * averaged_score["criteria__percentage"]

        return round(total, 2)

    def save(self, *args, **kwargs):
        if self._state.adding and not self.display_order:
            max_order = type(self).objects.aggregate(max_order=Max("display_order"))["max_order"] or 0
            self.display_order = max_order + 1

        super().save(*args, **kwargs)


class Judge(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class LiveCriteriaSession(models.Model):
    criterion = models.ForeignKey(Criteria, on_delete=models.CASCADE, related_name="live_sessions")
    activated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activated_live_sessions",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-activated_at", "-id"]

    def __str__(self):
        return f"{self.criterion.name} live session"


class LiveCriteriaSubmission(models.Model):
    session = models.ForeignKey(
        LiveCriteriaSession,
        on_delete=models.CASCADE,
        related_name="judge_submissions",
    )
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE, related_name="live_submissions")
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["submitted_at", "id"]
        unique_together = ("session", "judge")

    def __str__(self):
        return f"{self.judge} submitted {self.session.criterion.name}"


class Score(models.Model):

    judge = models.ForeignKey(Judge, on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    criteria = models.ForeignKey(Criteria, on_delete=models.CASCADE)

    score_value = models.IntegerField()

    class Meta:
        unique_together = ("judge", "participant", "criteria")
        indexes = [
            models.Index(fields=["judge", "criteria"]),
            models.Index(fields=["participant", "criteria"]),
        ]

    def weighted_score(self):
        return (self.score_value / 100) * self.criteria.percentage
