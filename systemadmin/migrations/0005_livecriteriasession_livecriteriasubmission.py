from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("systemadmin", "0004_criteria_display_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiveCriteriaSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("activated_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "activated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="activated_live_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "criterion",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="live_sessions",
                        to="systemadmin.criteria",
                    ),
                ),
            ],
            options={
                "ordering": ["-activated_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="LiveCriteriaSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_at", models.DateTimeField(auto_now=True)),
                (
                    "judge",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="live_submissions",
                        to="systemadmin.judge",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="judge_submissions",
                        to="systemadmin.livecriteriasession",
                    ),
                ),
            ],
            options={
                "ordering": ["submitted_at", "id"],
                "unique_together": {("session", "judge")},
            },
        ),
    ]
