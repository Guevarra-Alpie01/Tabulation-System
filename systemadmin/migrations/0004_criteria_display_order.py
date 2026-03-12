from django.db import migrations, models


def populate_display_order(apps, schema_editor):
    Criteria = apps.get_model("systemadmin", "Criteria")

    for index, criterion in enumerate(Criteria.objects.order_by("id"), start=1):
        criterion.display_order = index
        criterion.save(update_fields=["display_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("systemadmin", "0003_seed_default_tabulator_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="criteria",
            name="display_order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(populate_display_order, migrations.RunPython.noop),
    ]
