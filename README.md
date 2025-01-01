# DocuScout

DocuScout is a powerful documentation image scanner that helps you find and track documentation screenshots that need updating. Using advanced OCR technology and smart caching, it efficiently scans your documentation website and identifies images based on their content, URLs, and alt text.

## Features

- Scans XML sitemaps for documentation pages
- Performs OCR on images to find specific content
- Searches image URLs and alt text
- Smart caching system:
  - Caches downloaded images for faster subsequent runs
  - Caches page HTML with 24-hour expiry
  - Shows cache status for both pages and images
- Real-time progress tracking:
  - Overall progress bar with completion estimates
  - Current page being processed
  - Current image being processed
  - Processing speed in pages/second
- Handles various image formats:
  - PNG, JPG, RGBA images
  - Converts palette images with transparency
  - Skips SVG images automatically
- Dockerized for easy setup and use
- Supports multiple search terms
- Test mode for quick validation:
  - Randomly samples 5 pages
  - Outputs results directly to screen
- Outputs results to CSV (in non-test mode)

## Prerequisites

- Docker
- Docker Compose

That's all you need! Everything else is handled by the Docker container.

## Setup

1. Clone this repository:
```bash
git clone [repository-url]
cd docuscout
```

2. Make the script executable:
```bash
chmod +x docuscout
```

### Optional: Make DocuScout Globally Accessible

You can make DocuScout accessible from anywhere on your system by following these steps:

1. First, get the absolute path to your DocuScout installation:
```bash
cd /path/to/docuscout  # Navigate to where you cloned the repository
DOCUSCOUT_PATH=$(pwd)/docuscout
```

2. Create a symbolic link in `/usr/local/bin`:
```bash
sudo ln -s "$DOCUSCOUT_PATH" /usr/local/bin/docuscout
```

Now you can run DocuScout from any directory using just:
```bash
docuscout --sitemap "https://example.com/sitemap.xml" --search-terms "Term1" "Term2"
```

Notes:
- Make sure to use absolute paths when creating the symbolic link
- If you move the DocuScout directory after creating the symbolic link, you'll need to update the link
- You can check where the symlink points to with: `ls -l /usr/local/bin/docuscout`

## Usage

### Basic Usage

Run with required arguments:
```bash
./docuscout --sitemap "https://example.com/sitemap.xml" --search-terms "Term1" "Term2"
```
Or if installed globally:
```bash
docuscout --sitemap "https://example.com/sitemap.xml" --search-terms "Term1" "Term2"
```

### Quick Testing

Test mode (randomly samples 5 pages and outputs results to screen):
```bash
docuscout --sitemap "https://docs.example.com/sitemap.xml" --search-terms "Metabox" "Settings" --test
```

Example test output:
```
Test Results:
================================================================================
page_url,image_url,matched_term
docs/setup-guide,https://example.com/images/settings.png,Settings
docs/metabox,https://example.com/images/meta-options.jpg,Metabox
================================================================================
```

### Advanced Usage

Multiple search terms:
```bash
docuscout --sitemap "https://example.com/sitemap.xml" --search-terms "Download Button" "Settings Panel" "Configuration"
```

With cache clearing:
```bash
docuscout --sitemap "https://docs.example.com/sitemap.xml" --search-terms "Metabox" "Settings" --clear-cache
```

With custom output file:
```bash
docuscout --sitemap "https://docs.example.com/sitemap.xml" --search-terms "Feature" "Setup" --output "my_results.csv"
```

Full example with all options:
```bash
docuscout \
  --sitemap "https://docs.example.com/sitemap.xml" \
  --search-terms "Setup Guide" "Configuration" "API Settings" \
  --clear-cache \
  --output "documentation_audit.csv" \
  --test
```

## Output Format

The tool generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| page_url | URL of the page containing the image |
| image_url | Direct URL to the image |
| matched_term | The search term that matched |

Example output:
```csv
page_url,image_url,matched_term
https://example.com/docs/setup,https://example.com/images/settings.png,Settings Panel
https://example.com/docs/config,https://example.com/images/config.jpg,Configuration
```

## Cache System

The tool uses a two-level caching system:

### Image Cache
- Location: `cache/images/`
- Format: PNG files
- Naming: MD5 hash of image URL
- Persistence: Until manually cleared

### Page Cache
- Location: `cache/pages/`
- Format: JSON files with content and timestamp
- Expiry: 24 hours
- Naming: MD5 hash of page URL

Clear all caches:
```bash
docuscout --clear-cache
```

## Progress Display

The tool shows real-time progress with three components:
```
Scanning X pages for matching images...
Progress: 45%|████████               | 45/541 [00:30<00:37,  1.47 pages/s]
Page:  docs/setup-guide (✓)
Image: wp-content/uploads/screenshot.png (✓)
```

- Progress bar shows completion percentage and timing estimates
- Page status shows current page being processed (✓ = cached, ↓ = downloading)
- Image status shows current image being processed (✓ = cached, ↓ = downloading)

## Troubleshooting

### Common Issues

1. Cloudflare Protection
   - Symptom: Receiving HTML instead of XML from sitemap
   - Solution:
     - Reduce request frequency
     - Contact site administrator for API access
     - Try accessing through a different endpoint

2. OCR Quality
   - Symptom: Missing expected matches
   - Solutions:
     - Ensure images are clear and readable
     - Try variations of search terms
     - Check image cache for corrupted files

3. Permission Issues
   - Symptom: Cannot write to cache or output
   - Solutions:
     - Check folder permissions
     - Ensure run.sh is executable
     - Run with sudo if needed

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - feel free to use this tool for any purpose.

## Acknowledgments

- Uses Tesseract OCR for image text recognition
- Built with Python and Docker
- Inspired by the need to maintain up-to-date documentation screenshots
```

The README now includes:
1. New caching system details
2. Improved progress display information
3. Updated output format
4. More detailed troubleshooting
5. Better usage examples
6. Cache management details
