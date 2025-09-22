
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Frame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='Name of the frame project', max_length=200)),
                ('frame_image', models.ImageField(help_text='Upload frame JPG image', upload_to='frames/')),
                ('feed_url', models.URLField(default='https://cdn.goanalytix.io/assets/casestudy/CaseStudyFeed.xml', help_text='XML feed URL')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('coordinates_set', 'Coordinates Set'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='draft', help_text='Current processing status', max_length=20)),
                ('x_coordinate', models.PositiveIntegerField(default=0, help_text='X position (pixels from left)', validators=[django.core.validators.MinValueValidator(0)])),
                ('y_coordinate', models.PositiveIntegerField(default=0, help_text='Y position (pixels from top)', validators=[django.core.validators.MinValueValidator(0)])),
                ('width', models.PositiveIntegerField(default=100, help_text='Width of product overlay', validators=[django.core.validators.MinValueValidator(1)])),
                ('height', models.PositiveIntegerField(default=100, help_text='Height of product overlay', validators=[django.core.validators.MinValueValidator(1)])),
                ('total_products', models.PositiveIntegerField(default=0, help_text='Total number of products to process')),
                ('processed_products', models.PositiveIntegerField(default=0, help_text='Number of products processed')),
                ('failed_products', models.PositiveIntegerField(default=0, help_text='Number of products that failed processing')),
                ('processing_started_at', models.DateTimeField(blank=True, help_text='When processing started', null=True)),
                ('processing_completed_at', models.DateTimeField(blank=True, help_text='When processing completed', null=True)),
                ('coordinates_set', models.BooleanField(default=False, help_text='Whether coordinates have been set')),
                ('processing_started', models.BooleanField(default=False, help_text='Whether bulk processing has started')),
                ('processing_completed', models.BooleanField(default=False, help_text='Whether bulk processing is completed')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frames', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Output',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product_id', models.CharField(help_text='Product ID from XML feed', max_length=100)),
                ('product_image_url', models.URLField(help_text='Original product image URL from feed')),
                ('output_image', models.ImageField(help_text='Generated combined image', upload_to='outputs/')),
                ('frame', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outputs', to='app.frame')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('frame', 'product_id')},
            },
        ),
    ]
