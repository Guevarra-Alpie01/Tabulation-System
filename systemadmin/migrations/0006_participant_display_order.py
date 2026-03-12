from django.db import migrations, models


def populate_participant_display_order(apps, schema_editor):
    Participant = apps.get_model("systemadmin", "Participant")

    for index, participant in enumerate(Participant.objects.order_by("id"), start=1):
        participant.display_order = index
        participant.save(update_fields=["display_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("systemadmin", "0005_livecriteriasession_livecriteriasubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="display_order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(populate_participant_display_order, migrations.RunPython.noop),
    ]
