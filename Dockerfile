FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create uploads directory if it doesn't exist
RUN mkdir -p app/uploads

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "run.py"] 