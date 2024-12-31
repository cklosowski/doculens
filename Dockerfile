FROM python:3.11-slim

# Install system dependencies including Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create cache directories with proper permissions
RUN mkdir -p cache/images cache/pages \
    && chmod 777 cache cache/images cache/pages

# Command to run the script
ENTRYPOINT ["python", "docs-list.py"]