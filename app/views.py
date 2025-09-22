from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from .models import Frame, Output
from .forms import FrameCreateForm, CoordinateAdjustmentForm
from . import utils_functions
from .tasks import process_frame_bulk_output
from PIL import Image
import base64
from io import BytesIO
import json
import os
import logging

logger = logging.getLogger(__name__)


class CustomLoginView(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    frames = Frame.objects.filter(user=request.user)[:5]
    return render(request, 'app/dashboard.html', {'frames': frames})


@login_required
@require_http_methods(["GET", "POST"])
def frame_create(request):
    if request.method == 'POST':
        form = FrameCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    frame = form.save(commit=False)
                    frame.user = request.user
                    frame.save()
                    
                logger.info(f"User {request.user.username} created frame: {frame.name}")
                messages.success(request, f'Frame project "{frame.name}" created successfully!')
                return redirect('frame_preview', pk=frame.pk)
                
            except Exception as e:
                logger.error(f"Error creating frame for user {request.user.username}: {str(e)}")
                messages.error(request, 'An error occurred while creating the frame. Please try again.')
        else:
            logger.warning(f"Invalid frame creation form for user {request.user.username}: {form.errors}")
    else:
        form = FrameCreateForm()
    
    return render(request, 'app/frame_create.html', {'form': form})


@login_required
@require_http_methods(["GET", "POST"])
def frame_preview(request, pk):
    frame = get_object_or_404(Frame, pk=pk, user=request.user)
    
    # Get first product for preview
    first_product = None
    try:
        first_product = utils_functions.get_first_product_from_feed(frame.feed_url)
        if not first_product:
            messages.warning(request, 'No products found in the feed. Please check the feed URL.')
    except Exception as e:
        logger.error(f"Error fetching first product for frame {pk}: {str(e)}")
        messages.error(request, 'Error loading feed data. Please check the feed URL.')
    
    if request.method == 'POST':
        form = CoordinateAdjustmentForm(request.POST, instance=frame)
        if form.is_valid():
            try:
                with transaction.atomic():
                    frame = form.save(commit=False)
                    frame.coordinates_set = True
                    
                    # Update status if still draft
                    if frame.status == Frame.Status.DRAFT:
                        frame.status = Frame.Status.COORDINATES_SET
                    
                    frame.save()
                    
                logger.info(f"Coordinates saved for frame {pk} by user {request.user.username}")
                messages.success(request, 'Coordinates saved successfully!')
                
                # Start bulk processing if not already started
                if not frame.processing_started:
                    try:
                        task = process_frame_bulk_output.delay(frame.id)
                        logger.info(f"Started bulk processing task for frame {pk}")
                        messages.info(request, 'Bulk processing started in background!')
                    except Exception as e:
                        logger.error(f"Error starting bulk processing for frame {pk}: {str(e)}")
                        messages.warning(request, 'Coordinates saved, but bulk processing could not be started. Please try again later.')
                
                return redirect('frame_detail', pk=frame.pk)
                
            except Exception as e:
                logger.error(f"Error saving coordinates for frame {pk}: {str(e)}")
                messages.error(request, 'An error occurred while saving coordinates. Please try again.')
        else:
            logger.warning(f"Invalid coordinate form for frame {pk}: {form.errors}")
    else:
        form = CoordinateAdjustmentForm(instance=frame)
    
    context = {
        'frame': frame,
        'form': form,
        'first_product': first_product,
    }
    
    return render(request, 'app/frame_preview.html', context)


@login_required
@require_POST
def generate_preview_image(request, pk):
    frame = get_object_or_404(Frame, pk=pk, user=request.user)
    
    try:
        # Parse and validate input data
        data = json.loads(request.body)
        x = max(0, min(int(data.get('x', frame.x_coordinate)), 4000))
        y = max(0, min(int(data.get('y', frame.y_coordinate)), 4000))
        width = max(1, min(int(data.get('width', frame.width)), 2000))
        height = max(1, min(int(data.get('height', frame.height)), 2000))
        
        # Get first product from feed
        first_product = utils_functions.get_first_product_from_feed(frame.feed_url)
        if not first_product:
            logger.warning(f"No products found in feed for frame {pk}")
            return JsonResponse({'error': 'No products found in feed'}, status=400)
        
        # Generate preview image
        combined_image = utils_functions.overlay_product_on_frame(
            frame.frame_image.name,
            first_product['image_link'],
            x, y, width, height
        )
        
        # Optimize for preview (smaller size, lower quality)
        if combined_image.size[0] > 800 or combined_image.size[1] > 600:
            combined_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = BytesIO()
        combined_image.save(buffer, format='JPEG', quality=75, optimize=True)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info(f"Generated preview for frame {pk} with coordinates ({x}, {y}, {width}, {height})")
        
        return JsonResponse({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_str}'
        })
        
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in preview request for frame {pk}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError as e:
        logger.warning(f"Invalid coordinates in preview request for frame {pk}: {str(e)}")
        return JsonResponse({'error': 'Invalid coordinate values'}, status=400)
    except Exception as e:
        logger.error(f"Error generating preview for frame {pk}: {str(e)}")
        return JsonResponse({'error': 'Failed to generate preview'}, status=500)


@login_required
@cache_page(60 * 5)  # Cache for 5 minutes
def frame_list(request):
    frames = Frame.objects.filter(user=request.user).select_related('user')
    return render(request, 'app/frame_list.html', {'frames': frames})


@login_required
def frame_detail(request, pk):
    frame = get_object_or_404(
        Frame.objects.select_related('user').prefetch_related('outputs'), 
        pk=pk, 
        user=request.user
    )
    
    # Get some statistics
    total_outputs = frame.outputs.count()
    
    context = {
        'frame': frame,
        'total_outputs': total_outputs,
    }
    
    return render(request, 'app/frame_detail.html', context)


@login_required
def frame_outputs_data(request, pk):
    frame = get_object_or_404(Frame, pk=pk, user=request.user)
    
    try:
        # Parse DataTables parameters
        draw = int(request.GET.get('draw', 1))
        start = max(0, int(request.GET.get('start', 0)))
        length = min(100, max(1, int(request.GET.get('length', 10))))  # Limit to 100 per page
        search_value = request.GET.get('search[value]', '').strip()
        
        # Build queryset
        queryset = Output.objects.filter(frame=frame).select_related('frame')
        
        if search_value:
            queryset = queryset.filter(product_id__icontains=search_value)
        
        # Get counts
        total_records = Output.objects.filter(frame=frame).count()
        filtered_records = queryset.count()
        
        # Get paginated results
        outputs = queryset.order_by('-created_at')[start:start + length]
        
        # Build response data
        data = []
        for output in outputs:
            data.append([
                output.product_id,
                f'<img src="{output.output_image.url}" alt="Output" style="max-width: 100px; max-height: 100px; object-fit: cover;" loading="lazy">',
                output.created_at.strftime('%Y-%m-%d %H:%M'),
                f'<a href="{output.output_image.url}" target="_blank" class="btn btn-sm btn-primary">View Full</a>'
            ])
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        })
        
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid parameters in frame_outputs_data for frame {pk}: {str(e)}")
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Error in frame_outputs_data for frame {pk}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def frame_delete(request, pk):
    frame = get_object_or_404(Frame, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            frame_name = frame.name
            
            # Delete associated files
            try:
                if frame.frame_image and os.path.exists(frame.frame_image.path):
                    os.remove(frame.frame_image.path)
                
                # Delete output directory
                output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', str(frame.pk))
                if os.path.exists(output_dir):
                    import shutil
                    shutil.rmtree(output_dir)
                    
            except Exception as e:
                logger.warning(f"Error deleting files for frame {pk}: {str(e)}")
            
            # Delete database record
            with transaction.atomic():
                frame.delete()
            
            logger.info(f"User {request.user.username} deleted frame: {frame_name}")
            messages.success(request, f'Frame project "{frame_name}" deleted successfully!')
            return redirect('frame_list')
            
        except Exception as e:
            logger.error(f"Error deleting frame {pk}: {str(e)}")
            messages.error(request, 'An error occurred while deleting the frame. Please try again.')
            return redirect('frame_detail', pk=pk)
    
    return render(request, 'app/frame_confirm_delete.html', {'frame': frame})


# Health Check Views
def health_check(request):
    """Basic health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })


def health_check_db(request):
    """Database health check"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'database',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'database',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)


def health_check_redis(request):
    """Redis health check"""
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        
        if result == 'ok':
            return JsonResponse({
                'status': 'healthy',
                'service': 'redis',
                'timestamp': timezone.now().isoformat()
            })
        else:
            raise Exception("Cache test failed")
            
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'redis',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)


def health_metrics(request):
    """System metrics endpoint for monitoring"""
    try:
        from .monitoring import collect_system_metrics
        metrics = collect_system_metrics()
        
        # Add application-specific metrics
        from .models import Frame, Output
        metrics['application'] = {
            'total_frames': Frame.objects.count(),
            'processing_frames': Frame.objects.filter(status=Frame.Status.PROCESSING).count(),
            'completed_frames': Frame.objects.filter(status=Frame.Status.COMPLETED).count(),
            'total_outputs': Output.objects.count(),
        }
        
        return JsonResponse(metrics)
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        return JsonResponse({
            'error': 'Failed to collect metrics',
            'timestamp': timezone.now().isoformat()
        }, status=500)