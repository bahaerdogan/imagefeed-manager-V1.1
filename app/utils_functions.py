import xml.etree.ElementTree as ET
import requests
from PIL import Image
from io import BytesIO
import os
import socket
import ipaddress
from django.conf import settings
from django.core.cache import cache
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Security settings
ALLOWED_SCHEMES = {'http', 'https'}
BLOCKED_PORTS = {22, 23, 25, 53, 135, 139, 445, 993, 995, 1433, 1521, 3306, 3389, 5432, 5984, 6379}
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
]

REQUEST_TIMEOUT = 10
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB


def validate_url_security(url):
    """Validate URL to prevent SSRF attacks"""
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        
        # Check hostname
        if not parsed.hostname:
            raise ValueError("Invalid hostname")
        
        # Resolve IP and check for private ranges
        try:
            ip = socket.gethostbyname(parsed.hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            for private_range in PRIVATE_IP_RANGES:
                if ip_obj in private_range:
                    raise ValueError("Access to private IP ranges is not allowed")
                    
        except socket.gaierror:
            raise ValueError("Unable to resolve hostname")
        
        # Check port
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        if port in BLOCKED_PORTS:
            raise ValueError(f"Access to port {port} is not allowed")
        
        return True
        
    except Exception as e:
        logger.warning(f"URL validation failed for {url}: {str(e)}")
        raise ValueError(f"Invalid URL: {str(e)}")


def parse_xml_feed(feed_url):
    """
    Parse XML feed and return list of products with id and image_link.
    
    Args:
        feed_url (str): URL of the XML feed
        
    Returns:
        list: List of dictionaries with 'id' and 'image_link' keys
    """
    # Check cache first
    cache_key = f"feed_data_{hash(feed_url)}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Using cached feed data for {feed_url}")
        return cached_data
    
    try:
        # Validate URL for security
        validate_url_security(feed_url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; FeedProcessor/1.0)',
            'Accept': 'application/xml, text/xml, */*'
        }
        
        response = requests.get(
            feed_url, 
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            stream=True
        )
        response.raise_for_status()
        
        # Check content length
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            raise ValueError(f"Feed too large: {content_length} bytes")
        
        # Read content with size limit
        content = b''
        downloaded_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            downloaded_size += len(chunk)
            if downloaded_size > MAX_CONTENT_LENGTH:
                raise ValueError("Feed content exceeds maximum size")
            content += chunk
        
        root = ET.fromstring(content)
        
        # Handle namespaces
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'g': 'http://base.google.com/ns/1.0'
        }
        
        products = []
        
        # Find all entry elements - they are in the Atom namespace
        entries = root.findall('.//atom:entry', namespaces)
        if not entries:
            # Fallback: try without namespace
            entries = root.findall('.//entry')
        
        for entry in entries:
            product_id = None
            image_link = None
            
            # Elements are in the Atom namespace
            id_elem = entry.find('atom:id', namespaces)
            if id_elem is not None and id_elem.text:
                product_id = id_elem.text.strip()
            
            image_elem = entry.find('atom:image_link', namespaces)
            if image_elem is not None and image_elem.text:
                image_link = image_elem.text.strip()
            
            if product_id and image_link:
                products.append({
                    'id': product_id,
                    'image_link': image_link
                })
        
        # Cache the results for 30 minutes
        cache.set(cache_key, products, 1800)
        logger.info(f"Parsed {len(products)} products from feed {feed_url}")
        
        return products
        
    except requests.RequestException as e:
        logger.error(f"Error fetching feed {feed_url}: {str(e)}")
        raise Exception(f"Error fetching feed: {str(e)}")
    except ET.ParseError as e:
        logger.error(f"Error parsing XML from {feed_url}: {str(e)}")
        raise Exception(f"Error parsing XML: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error parsing feed {feed_url}: {str(e)}")
        raise Exception(f"Unexpected error: {str(e)}")


def download_image(url):
    """
    Download image from URL and return PIL Image object.
    
    Args:
        url (str): URL of the image
        
    Returns:
        PIL.Image: Downloaded image
    """
    # Check cache first
    cache_key = f"image_{hash(url)}"
    
    try:
        # Validate URL for security
        validate_url_security(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ImageProcessor/1.0)',
            'Accept': 'image/*'
        }
        
        response = requests.get(
            url, 
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            stream=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if content_type and not any(mime in content_type for mime in ['image/jpeg', 'image/png', 'image/webp']):
            raise ValueError(f"Invalid content type: {content_type}")
        
        # Check content length
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            raise ValueError(f"Image too large: {content_length} bytes")
        
        # Read content with size limit
        image_data = BytesIO()
        downloaded_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            downloaded_size += len(chunk)
            if downloaded_size > 10 * 1024 * 1024:  # 10MB
                raise ValueError("Image exceeds size limit")
            image_data.write(chunk)
        
        image_data.seek(0)
        image = Image.open(image_data)
        
        # Convert to RGB if necessary (handles RGBA, P mode images)
        if image.mode in ('RGBA', 'P', 'LA'):
            image = image.convert('RGB')
        
        # Validate image dimensions
        if image.size[0] > 4000 or image.size[1] > 4000:
            raise ValueError(f"Image dimensions too large: {image.size}")
        
        if image.size[0] < 10 or image.size[1] < 10:
            raise ValueError(f"Image dimensions too small: {image.size}")
        
        logger.info(f"Downloaded image from {url}, size: {image.size}")
        return image
        
    except requests.RequestException as e:
        logger.error(f"Error downloading image from {url}: {str(e)}")
        raise Exception(f"Error downloading image: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing image from {url}: {str(e)}")
        raise Exception(f"Error processing image: {str(e)}")


def overlay_product_on_frame(frame_image_path, product_image_url, x, y, width, height):
    """
    Overlay product image on frame at specified coordinates.
    
    Args:
        frame_image_path (str): Path to the frame image
        product_image_url (str): URL of the product image
        x (int): X coordinate for overlay
        y (int): Y coordinate for overlay
        width (int): Width of the overlay
        height (int): Height of the overlay
        
    Returns:
        PIL.Image: Combined image
    """
    try:
        # Validate coordinates
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise ValueError(f"Invalid coordinates: x={x}, y={y}, width={width}, height={height}")
        
        # Open frame image
        frame_path = os.path.join(settings.MEDIA_ROOT, frame_image_path)
        if not os.path.exists(frame_path):
            raise FileNotFoundError(f"Frame image not found: {frame_path}")
        
        frame = Image.open(frame_path)
        
        # Validate overlay bounds
        if x + width > frame.size[0] or y + height > frame.size[1]:
            raise ValueError(f"Overlay extends beyond frame boundaries. Frame: {frame.size}, Overlay: ({x}, {y}, {width}, {height})")
        
        # Download and resize product image
        product = download_image(product_image_url)
        product = product.resize((width, height), Image.Resampling.LANCZOS)
        
        # Create a copy of frame to avoid modifying original
        result = frame.copy()
        
        # Paste product image onto frame
        if product.mode == 'RGBA':
            result.paste(product, (x, y), product)
        else:
            result.paste(product, (x, y))
        
        logger.info(f"Successfully overlaid product on frame at ({x}, {y}) with size ({width}, {height})")
        return result
        
    except Exception as e:
        logger.error(f"Error overlaying images: {str(e)}")
        raise Exception(f"Error overlaying images: {str(e)}")


def save_output_image(image, frame_id, product_id):
    """
    Save the combined image to outputs directory.
    
    Args:
        image (PIL.Image): Image to save
        frame_id (int): Frame ID
        product_id (str): Product ID
        
    Returns:
        str: Relative path to saved image
    """
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', str(frame_id))
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize product_id for filename
        safe_product_id = "".join(c for c in str(product_id) if c.isalnum() or c in ('-', '_'))[:50]
        if not safe_product_id:
            safe_product_id = f"product_{hash(product_id) % 10000}"
        
        # Generate filename
        filename = f"{safe_product_id}.jpg"
        file_path = os.path.join(output_dir, filename)
        
        # Optimize image before saving
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save image with optimization
        image.save(file_path, 'JPEG', quality=85, optimize=True)
        
        # Return relative path for database storage
        relative_path = os.path.join('outputs', str(frame_id), filename)
        logger.info(f"Saved output image: {relative_path}")
        
        return relative_path
        
    except Exception as e:
        logger.error(f"Error saving image for frame {frame_id}, product {product_id}: {str(e)}")
        raise Exception(f"Error saving image: {str(e)}")


def get_first_product_from_feed(feed_url):
    """
    Get the first product from the XML feed for preview.
    
    Args:
        feed_url (str): URL of the XML feed
        
    Returns:
        dict: First product with 'id' and 'image_link' keys, or None if no products
    """
    try:
        products = parse_xml_feed(feed_url)
        if products:
            logger.info(f"Retrieved first product from feed: {products[0]['id']}")
            return products[0]
        else:
            logger.warning(f"No products found in feed: {feed_url}")
            return None
    except Exception as e:
        logger.error(f"Error getting first product from feed {feed_url}: {str(e)}")
        return None
