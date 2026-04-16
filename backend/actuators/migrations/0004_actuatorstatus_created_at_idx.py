from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actuators', '0003_remove_actuator_readings'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='actuatorstatus',
            index=models.Index(fields=['created_at'], name='actuators_ac_created_idx'),
        ),
    ]
