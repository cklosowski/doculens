import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
from io import BytesIO
import cv2
from xml.etree import ElementTree as ET
import html
from io import StringIO
import defusedxml.ElementTree as SafeET
import csv
import pytesseract
import tempfile
import os
import hashlib
from pathlib import Path
import argparse
from tqdm import tqdm
import sys
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import threading

CACHE_DIR = Path('cache/images')
CACHE_DIR.mkdir(parents=True, exist_ok=True)
PAGE_CACHE_DIR = Path('cache/pages')
PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
PAGE_CACHE_EXPIRY = timedelta(days=1)  # Cache pages for 1 day
MAX_WORKERS = 3  # Default number of concurrent image processors
status_lock = threading.Lock()
image_queue = queue.Queue()

def get_cache_path(url):
    """Generate a cache file path for a given URL"""
    # Create a hash of the URL to use as filename
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.png"

def get_page_cache_path(url):
    """Generate a cache file path for a page URL"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return PAGE_CACHE_DIR / f"{url_hash}.json"

def get_cached_page(url):
    """Get page content from cache if available and not expired"""
    cache_path = get_page_cache_path(url)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                cached_time = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - cached_time < PAGE_CACHE_EXPIRY:
                    return cached_data['content']
        except Exception as e:
            pass
    return None

def cache_page(url, content):
    """Cache page content with timestamp"""
    cache_path = get_page_cache_path(url)
    try:
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'content': content
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
    except Exception as e:
        pass

def download_image(url):
    """Download image from URL and return PIL Image object, using cache if available"""
    try:
        # Check cache first
        cache_path = get_cache_path(url)
        if cache_path.exists():
            return Image.open(cache_path)

        # Handle data URLs and regular URLs
        if url.startswith('data:image'):
            header, data = url.split(',', 1)
            if ';base64' in header:
                image_data = base64.b64decode(data)
                img = Image.open(BytesIO(image_data))
            else:
                return None
        else:
            response = requests.get(url)
            if not response.headers.get('content-type', '').startswith('image/'):
                return None
            img = Image.open(BytesIO(response.content))

        # Handle image formats
        if img.mode == 'P':
            try:
                img = img.convert('RGBA')
            except:
                return None

        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        # Save to cache
        img.save(cache_path, 'PNG')
        return img
    except:
        return None

def perform_ocr(image):
    """Perform OCR on an image and return the text"""
    try:
        if image.mode not in ['RGB', 'L']:
            image = image.convert('RGB')

        max_dimension = 4000
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        text = pytesseract.image_to_string(image)
        return text.lower()
    except:
        return ""

def process_image(args):
    """Process a single image with all necessary checks and OCR"""
    page_url, img, search_strings = args
    img_url = img.get('src')
    if not img_url:
        return None

    if not img_url.startswith(('http://', 'https://')):
        img_url = requests.compat.urljoin(page_url, img_url)

    if 'svg' in img_url.lower() or img_url.startswith('data:image/svg'):
        return None

    # Check if image is cached
    cache_path = get_cache_path(img_url)
    img_cached = cache_path.exists()

    # Remove the status update since we're processing in parallel
    # Download and process image
    image = download_image(img_url)
    if image is None:
        return None

    # Perform OCR and check for matches
    ocr_text = perform_ocr(image)
    img_alt = img.get('alt', '').lower()

    for search_string in search_strings:
        search_string_lower = search_string.lower()
        if (search_string_lower in ocr_text or
            search_string_lower in img_url.lower() or
            search_string_lower in img_alt):

            return {
                'page_url': page_url,
                'image_url': img_url,
                'matched_term': search_string
            }
    return None

def find_similar_images(sitemap_url, search_strings=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        'Accept': 'text/html,application/xml,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    # Silence other output
    sys.stdout = open(os.devnull, 'w')

    response = requests.get(sitemap_url, headers=headers)
    matching_images = []

    # Check if we got XML or HTML
    content_type = response.headers.get('Content-Type', '').lower()
    if 'html' in content_type or response.content.strip().startswith(b'<!DOCTYPE html'):
        print("Error: Received HTML instead of XML - likely blocked by Cloudflare", file=sys.stderr)
        return []

    # Handle XML entities properly
    try:
        root = SafeET.fromstring(response.content)
    except Exception as e:
        try:
            content = response.content.decode('utf-8')
            content = html.unescape(content)
            root = ET.fromstring(content.encode('utf-8'))
        except Exception as inner_e:
            print(f"Error parsing XML: {inner_e}", file=sys.stderr)
            return []

    # Get all URLs first
    urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
    total_urls = len(urls)

    # Restore stdout for progress bar
    sys.stdout = sys.__stdout__

    print(f"\nScanning {total_urls} pages for matching images...")

    # Initialize just the progress and page status bars
    pbar = tqdm(total=total_urls,
                desc="Progress",
                position=0,
                leave=True,
                dynamic_ncols=True,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt:>9s}]',
                unit='pages',
                unit_scale=False,
                mininterval=1.0)

    page_status = tqdm(total=0,
                      position=1,
                      leave=True,
                      dynamic_ncols=True,
                      bar_format='{desc}',
                      mininterval=0.5)

    def format_url(url):
        """Format URL to remove hostname but keep full path"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # Keep the full path without modifying it
        path = parsed.path
        if path.startswith('/'):
            path = path[1:]  # Remove leading slash
        # If there's a query string, add it back
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path[:100]  # Still limit length to prevent overflow

    def update_status(page_url, page_cached):
        """Update status bar with current progress"""
        page_path = format_url(page_url)
        page_status.set_description_str(f"Page:  {page_path} ({'✓' if page_cached else '↓'})")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        try:
            for url in urls:
                page_url = url.text
                try:
                    # Check page cache first
                    page_content = get_cached_page(page_url)
                    page_cached = page_content is not None

                    # Update status for current page
                    update_status(page_url, page_cached)

                    if not page_cached:
                        response = requests.get(page_url)
                        page_content = response.text
                        cache_page(page_url, page_content)

                    soup = BeautifulSoup(page_content, 'html.parser')
                    entry_content = soup.find('div', class_='entry-content')

                    if not entry_content:
                        pbar.update(1)
                        continue

                    # Submit all images from this page to the thread pool
                    future_to_img = {
                        executor.submit(process_image, (page_url, img, search_strings)): img
                        for img in entry_content.find_all('img')
                    }

                    # Process completed futures
                    for future in as_completed(future_to_img):
                        result = future.result()
                        if result:
                            matching_images.append(result)

                except Exception as e:
                    print(f"\nError processing {page_url}: {str(e)}", file=sys.stderr)
                finally:
                    pbar.update(1)
                    # Reset image status when done with page
                    update_status(page_url, page_cached)

        finally:
            # Clear status bars before closing
            page_status.clear()
            pbar.close()
            page_status.close()

    print(f"\nFound {len(matching_images)} matching images")
    return matching_images

def save_to_csv(matching_images, output_file='matching_images.csv'):
    """Save the matching images results to a CSV file"""
    if not matching_images:
        print("No matching images found to save")
        return

    # Define the CSV headers
    fieldnames = ['page_url', 'image_url', 'alt_text', 'ocr_text', 'matched_term']

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matching_images)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

def clear_image_cache():
    """Clear the image cache directory"""
    try:
        for file in CACHE_DIR.glob('*'):
            file.unlink()
        print("Image cache cleared")
    except Exception as e:
        print(f"Error clearing cache: {e}")

def clear_cache():
    """Clear both image and page caches"""
    try:
        for file in CACHE_DIR.glob('*'):
            file.unlink()
        for file in PAGE_CACHE_DIR.glob('*'):
            file.unlink()
        print("Cache cleared")
    except Exception as e:
        print(f"Error clearing cache: {e}")

def main():
    parser = argparse.ArgumentParser(description='Scan documentation for images matching search terms')
    parser.add_argument('--sitemap',
                       required=True,
                       help='URL of the sitemap to scan')
    parser.add_argument('--search-terms',
                       nargs='+',
                       required=True,
                       help='List of terms to search for in images')
    parser.add_argument('--clear-cache',
                       action='store_true',
                       help='Clear all caches before running')
    parser.add_argument('--output',
                       default='matching_images.csv',
                       help='Output CSV file path')
    parser.add_argument('--workers',
                       type=int,
                       default=3,
                       help='Number of concurrent image processors (default: 3)')

    args = parser.parse_args()

    global MAX_WORKERS
    MAX_WORKERS = args.workers

    if args.clear_cache:
        clear_cache()

    matching_images = find_similar_images(
        args.sitemap,
        search_strings=args.search_terms
    )
    save_to_csv(matching_images, args.output)

if __name__ == "__main__":
    main()