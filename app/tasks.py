from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Frame, Output
from . import utils_functions
import logging
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_frame_bulk_output(self, frame_id):
    """
    Process all products in a frame's feed and generate output images.
    
    Args:
        frame_id (int): ID of the frame to process
        
    Returns:
        dict: Processing results
    """
    frame = None
    
    try:
        # Get and validate frame
        frame = Frame.objects.select_for_update().get(id=frame_id)
        
        if frame.status == Frame.Status.PROCESSING:
            logger.warning(f"Frame {frame_id} is already being processed")
            return {'success': False, 'error': 'Frame is already being processed'}
        
        # Start processing
        with transaction.atomic():
            frame.status = Frame.Status.PROCESSING
            frame.processing_started = True
            frame.processing_started_at = timezone.now()
            frame.processing_completed_at = None
            frame.processed_products = 0
            frame.failed_products = 0
            frame.save()
        
        logger.info(f"Started processing frame {frame_id}: {frame.name}")
        
        # Parse feed
        try:
            products = utils_functions.parse_xml_feed(frame.feed_url)
        except Exception as e:
            logger.error(f"Failed to parse feed for frame {frame_id}: {str(e)}")
            frame.status = Frame.Status.FAILED
            frame.processing_completed_at = timezone.now()
            frame.save()
            return {'success': False, 'error': f'Failed to parse feed: {str(e)}'}
        
        if not products:
            logger.warning(f"No products found in feed for frame {frame_id}")
            frame.status = Frame.Status.FAILED
            frame.processing_completed_at = timezone.now()
            frame.save()
            return {'success': False, 'error': 'No products found in feed'}
        
        # Update total products count
        frame.total_products = len(products)
        frame.save()
        
        processed_count = 0
        failed_count = 0
        
        # Process each product
        for i, product in enumerate(products):
            try:
                product_id = product.get('id')
                image_link = product.get('image_link')
                
                if not product_id or not image_link:
                    logger.warning(f"Invalid product data in frame {frame_id}: {product}")
                    failed_count += 1
                    continue
                
                # Skip if already processed
                if Output.objects.filter(frame=frame, product_id=product_id).exists():
                    logger.info(f"Product {product_id} already processed for frame {frame_id}")
                    processed_count += 1
                    continue
                
                # Generate combined image
                combined_image = utils_functions.overlay_product_on_frame(
                    frame.frame_image.name,
                    image_link,
                    frame.x_coordinate,
                    frame.y_coordinate,
                    frame.width,
                    frame.height
                )
                
                # Save output image
                output_path = utils_functions.save_output_image(
                    combined_image,
                    frame.id,
                    product_id
                )
                
                # Create database record
                with transaction.atomic():
                    Output.objects.create(
                        frame=frame,
                        product_id=product_id,
                        product_image_url=image_link,
                        output_image=output_path
                    )
                
                processed_count += 1
                
                # Update progress every 10 products
                if (i + 1) % 10 == 0:
                    frame.processed_products = processed_count
                    frame.failed_products = failed_count
                    frame.save()
                    logger.info(f"Frame {frame_id} progress: {processed_count}/{len(products)} processed")
                
            except Exception as e:
                logger.error(f"Failed to process product {product.get('id', 'unknown')} in frame {frame_id}: {str(e)}")
                failed_count += 1
                
                # If too many failures, stop processing
                if failed_count > len(products) * 0.5:  # More than 50% failed
                    logger.error(f"Too many failures in frame {frame_id}, stopping processing")
                    break
        
        # Update final status
        with transaction.atomic():
            frame.processed_products = processed_count
            frame.failed_products = failed_count
            frame.processing_completed = True
            frame.processing_completed_at = timezone.now()
            
            if processed_count > 0:
                frame.status = Frame.Status.COMPLETED
            else:
                frame.status = Frame.Status.FAILED
                
            frame.save()
        
        result = {
            'success': True,
            'processed': processed_count,
            'failed': failed_count,
            'total': len(products),
            'frame_id': frame_id
        }
        
        logger.info(f"Completed processing frame {frame_id}: {result}")
        return result
        
    except Frame.DoesNotExist:
        logger.error(f"Frame with ID {frame_id} not found")
        return {'success': False, 'error': 'Frame not found'}
        
    except Exception as e:
        logger.error(f"Unexpected error processing frame {frame_id}: {str(e)}")
        
        # Update frame status on error
        if frame:
            try:
                with transaction.atomic():
                    frame.status = Frame.Status.FAILED
                    frame.processing_completed_at = timezone.now()
                    frame.save()
            except Exception as save_error:
                logger.error(f"Failed to update frame status after error: {str(save_error)}")
        
        # Retry on certain errors with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)
            logger.info(f"Retrying frame {frame_id} processing (attempt {self.request.retries + 1}) in {retry_delay}s")
            raise self.retry(countdown=retry_delay, exc=e)
        
        return {'success': False, 'error': str(e), 'retries_exhausted': True}