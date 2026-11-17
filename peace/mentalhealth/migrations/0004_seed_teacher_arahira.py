from django.db import migrations


def seed_teacher(apps, schema_editor):
    Teacher = apps.get_model('mentalhealth', 'Teacher')
    Teacher.objects.get_or_create(
        email='arahira@kiis.ac.jp',
        defaults={
            'name': '荒平 高章',
            'department': '経営情報学部　情報ネットワーク学科',
            'position': '教授',
            'degree': '博士（工学）',
        },
    )


def remove_teacher(apps, schema_editor):
    Teacher = apps.get_model('mentalhealth', 'Teacher')
    Teacher.objects.filter(email='arahira@kiis.ac.jp').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mentalhealth', '0003_teacher_degree_teacher_position'),
    ]

    operations = [
        migrations.RunPython(seed_teacher, remove_teacher),
    ]
