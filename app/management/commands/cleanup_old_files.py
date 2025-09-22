from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os
import shutil
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old output files and orphaned media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete files older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"Cleaning up files older than {days} days...")
        if dry_run:
            self.stdout.write("DRY RUN - No files will be deleted")
        
        # Clean up output directories for deleted frames
        outputs_dir = os.path.join(settings.MEDIA_ROOT, 'outputs')
        if os.path.exists(outputs_dir):
            deleted_count = 0
            for frame_dir in os.listdir(outputs_dir):
                frame_path = os.path.join(outputs_dir, frame_dir)
                if os.path.isdir(frame_path):
                    # Check if frame still exists in database
                    from app.models import Frame
                    try:
                        Frame.objects.get(id=int(frame_dir))
                    except (Frame.DoesNotExist, ValueError):
                        # Frame doesn't exist, delete directory
                        if dry_run:
                            self.stdout.write(f"Would delete: {frame_path}")
                        else:
                            shutil.rmtree(frame_path)
                            self.stdout.write(f"Deleted: {frame_path}")
                        deleted_count += 1
            
            self.stdout.write(f"Cleaned up {deleted_count} orphaned output directories")
        
        # Clean up old log files
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        if os.path.exists(logs_dir):
            log_files_deleted = 0
            for log_file in os.listdir(logs_dir):
                if log_file.endswith('.log') and not log_file == 'django.log':
                    log_path = os.path.join(logs_dir, log_file)
                    if os.path.getmtime(log_path) < cutoff_date.timestamp():
                        if dry_run:
                            self.stdout.write(f"Would delete log: {log_path}")
                        else:
                            os.remove(log_path)
                            self.stdout.write(f"Deleted log: {log_path}")
                        log_files_deleted += 1
            
            self.stdout.write(f"Cleaned up {log_files_deleted} old log files")
        
        self.stdout.write("Cleanup completed successfully")