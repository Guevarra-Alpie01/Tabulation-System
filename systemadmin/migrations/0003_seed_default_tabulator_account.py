from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


DEFAULT_ADMIN_USERNAME = "tabulator_admin"
DEFAULT_ADMIN_PASSWORD = "tabulator123"


def create_default_tabulator_account(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    user, created = User.objects.get_or_create(
        username=DEFAULT_ADMIN_USERNAME,
        defaults={
            "is_staff": True,
            "is_active": True,
            "first_name": "Admin",
            "last_name": "Tabulator",
        },
    )

    if created:
        user.password = make_password(DEFAULT_ADMIN_PASSWORD)
        user.save()
        return

    updated = False
    if not user.is_staff:
        user.is_staff = True
        updated = True
    if not user.is_active:
        user.is_active = True
        updated = True

    if updated:
        user.save()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("systemadmin", "0002_rename_percentage_weight_criteria_percentage"),
    ]

    operations = [
        migrations.RunPython(create_default_tabulator_account, migrations.RunPython.noop),
    ]
