from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
import logging

logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


def validate_image_file(value):
    """Validate uploaded image file"""
    if not value:
        return
    
    if value.size > 10 * 1024 * 1024:  # 10MB
        raise ValidationError('File size cannot exceed 10MB.')
    
    valid_extensions = ['.jpg', '.jpeg']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Only JPG/JPEG files are allowed.')


class Frame(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        COORDINATES_SET = 'coordinates_set', 'Coordinates Set'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='frames', db_index=True)
    name = models.CharField(max_length=200, help_text="Name of the frame project")
    frame_image = models.ImageField(
        upload_to='frames/', 
        help_text="Upload frame JPG image",
        validators=[validate_image_file]
    )
    feed_url = models.URLField(
        default='https://cdn.goanalytix.io/assets/casestudy/CaseStudyFeed.xml',
        help_text="XML feed URL",
        validators=[URLValidator()]
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT,
        help_text="Current processing status",
        db_index=True
    )
    
    x_coordinate = models.PositiveIntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(4000)],
        help_text="X position (pixels from left)"
    )
    y_coordinate = models.PositiveIntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(4000)],
        help_text="Y position (pixels from top)"
    )
    width = models.PositiveIntegerField(
        default=100, 
        validators=[MinValueValidator(1), MaxValueValidator(2000)],
        help_text="Width of product overlay"
    )
    height = models.PositiveIntegerField(
        default=100, 
        validators=[MinValueValidator(1), MaxValueValidator(2000)],
        help_text="Height of product overlay"
    )
    
    total_products = models.PositiveIntegerField(default=0, help_text="Total number of products to process")
    processed_products = models.PositiveIntegerField(default=0, help_text="Number of products processed")
    failed_products = models.PositiveIntegerField(default=0, help_text="Number of products that failed processing")
    processing_started_at = models.DateTimeField(null=True, blank=True, help_text="When processing started")
    processing_completed_at = models.DateTimeField(null=True, blank=True, help_text="When processing completed")
    
    coordinates_set = models.BooleanField(default=False, help_text="Whether coordinates have been set")
    processing_started = models.BooleanField(default=False, help_text="Whether bulk processing has started")
    processing_completed = models.BooleanField(default=False, help_text="Whether bulk processing is completed")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('frame_detail', kwargs={'pk': self.pk})
    
    def get_output_directory(self):
        """Get the directory path where output images are stored."""
        return os.path.join('media', 'outputs', str(self.pk))
    
    @property
    def progress_percentage(self):
        if self.total_products == 0:
            return 0.0
        return (self.processed_products / self.total_products) * 100
    
    @property
    def success_rate(self):
        if self.processed_products == 0:
            return 0.0
        successful = self.processed_products - self.failed_products
        return (successful / self.processed_products) * 100
    
    @property
    def processing_duration(self):
        if not self.processing_started_at:
            return None
        end_time = self.processing_completed_at or timezone.now()
        return end_time - self.processing_started_at
    
    def can_start_processing(self):
        return (
            self.status in [self.Status.COORDINATES_SET, self.Status.FAILED] and
            self.coordinates_set and
            self.x_coordinate >= 0 and
            self.y_coordinate >= 0 and
            self.width > 0 and
            self.height > 0
        )
    
    def start_processing(self):
        if not self.can_start_processing():
            raise ValueError("Frame is not ready for processing")
        
        self.status = self.Status.PROCESSING
        self.processing_started_at = timezone.now()
        self.processing_completed_at = None
        self.processed_products = 0
        self.failed_products = 0
        self.save(update_fields=[
            'status', 'processing_started_at', 'processing_completed_at',
            'processed_products', 'failed_products'
        ])
    
    def complete_processing(self, success=True):
        if self.status != self.Status.PROCESSING:
            raise ValueError("Frame is not currently processing")
        
        self.status = self.Status.COMPLETED if success else self.Status.FAILED
        self.processing_completed_at = timezone.now()
        self.save(update_fields=['status', 'processing_completed_at'])
    
    def update_progress(self, processed_count=None, failed_count=None):
        if processed_count is not None:
            self.processed_products = processed_count
        if failed_count is not None:
            self.failed_products = failed_count
        
        update_fields = []
        if processed_count is not None:
            update_fields.append('processed_products')
        if failed_count is not None:
            update_fields.append('failed_products')
        
        if update_fields:
            self.save(update_fields=update_fields)
    
    def set_coordinates(self, x, y, width, height):
        self.x_coordinate = max(0, x)
        self.y_coordinate = max(0, y)
        self.width = max(1, width)
        self.height = max(1, height)
        self.coordinates_set = True
        
        if self.status == self.Status.DRAFT:
            self.status = self.Status.COORDINATES_SET
        
        self.save(update_fields=[
            'x_coordinate', 'y_coordinate', 'width', 'height', 
            'coordinates_set', 'status'
        ])


class Output(BaseModel):
    """Model to store generated output images."""
    
    frame = models.ForeignKey(Frame, on_delete=models.CASCADE, related_name='outputs')
    product_id = models.CharField(max_length=100, help_text="Product ID from XML feed")
    product_image_url = models.URLField(help_text="Original product image URL from feed")
    output_image = models.ImageField(upload_to='outputs/', help_text="Generated combined image")
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['frame', 'product_id']
        indexes = [
            models.Index(fields=['frame', '-created_at']),
            models.Index(fields=['product_id']),
        ]
    
    def __str__(self):
        return f"{self.frame.name} - {self.product_id}"



