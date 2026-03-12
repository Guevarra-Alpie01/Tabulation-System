from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("systemadmin", "0006_participant_display_order"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="score",
            index=models.Index(fields=["judge", "criteria"], name="systemadmin_judge_i_02109a_idx"),
        ),
        migrations.AddIndex(
            model_name="score",
            index=models.Index(fields=["participant", "criteria"], name="systemadmin_partici_cf5af3_idx"),
        ),
    ]
