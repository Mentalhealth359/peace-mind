from django.db import migrations


def seed_teacher(apps, schema_editor):
    Teacher = apps.get_model('mentalhealth', 'Teacher')
    Teacher.objects.get_or_create(
        email='manjusunar359@gmail.com',
        defaults={
            'name': 'Manju Sunar',
            'department': '',
            'position': '',
            'degree': '',
        },
    )


def remove_teacher(apps, schema_editor):
    Teacher = apps.get_model('mentalhealth', 'Teacher')
    Teacher.objects.filter(email='manjusunar359@gmail.com').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mentalhealth', '0004_seed_teacher_arahira'),
    ]

    operations = [
        migrations.RunPython(seed_teacher, remove_teacher),
    ]
