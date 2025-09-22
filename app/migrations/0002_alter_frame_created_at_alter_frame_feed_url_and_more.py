
import app.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frame',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='frame',
            name='feed_url',
            field=models.URLField(default='https://cdn.goanalytix.io/assets/casestudy/CaseStudyFeed.xml', help_text='XML feed URL', validators=[django.core.validators.URLValidator()]),
        ),
        migrations.AlterField(
            model_name='frame',
            name='frame_image',
            field=models.ImageField(help_text='Upload frame JPG image', upload_to='frames/', validators=[app.models.validate_image_file]),
        ),
        migrations.AlterField(
            model_name='frame',
            name='height',
            field=models.PositiveIntegerField(default=100, help_text='Height of product overlay', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2000)]),
        ),
        migrations.AlterField(
            model_name='frame',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('coordinates_set', 'Coordinates Set'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], db_index=True, default='draft', help_text='Current processing status', max_length=20),
        ),
        migrations.AlterField(
            model_name='frame',
            name='width',
            field=models.PositiveIntegerField(default=100, help_text='Width of product overlay', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2000)]),
        ),
        migrations.AlterField(
            model_name='frame',
            name='x_coordinate',
            field=models.PositiveIntegerField(default=0, help_text='X position (pixels from left)', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(4000)]),
        ),
        migrations.AlterField(
            model_name='frame',
            name='y_coordinate',
            field=models.PositiveIntegerField(default=0, help_text='Y position (pixels from top)', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(4000)]),
        ),
        migrations.AlterField(
            model_name='output',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddIndex(
            model_name='frame',
            index=models.Index(fields=['user', '-created_at'], name='app_frame_user_id_ba9176_idx'),
        ),
        migrations.AddIndex(
            model_name='frame',
            index=models.Index(fields=['status', '-created_at'], name='app_frame_status_16ac0d_idx'),
        ),
        migrations.AddIndex(
            model_name='output',
            index=models.Index(fields=['frame', '-created_at'], name='app_output_frame_i_ea634b_idx'),
        ),
        migrations.AddIndex(
            model_name='output',
            index=models.Index(fields=['product_id'], name='app_output_product_85d4a9_idx'),
        ),
    ]
