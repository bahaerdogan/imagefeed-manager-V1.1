from django.contrib import admin
from .models import Frame, Output


@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'coordinates_set', 'processing_completed', 'created_at']
    list_filter = ['coordinates_set', 'processing_completed', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'frame_image', 'feed_url')
        }),
        ('Coordinates', {
            'fields': ('x_coordinate', 'y_coordinate', 'width', 'height', 'coordinates_set')
        }),
        ('Processing Status', {
            'fields': ('processing_started', 'processing_completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Output)
class OutputAdmin(admin.ModelAdmin):
    list_display = ['frame', 'product_id', 'created_at']
    list_filter = ['created_at', 'frame']
    search_fields = ['product_id', 'frame__name']
    readonly_fields = ['created_at']
