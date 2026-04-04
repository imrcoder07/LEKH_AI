# Use an official lightweight Python image
FROM python:3.10-slim

# Prevent Python from writing pyc files to disc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (OpenCV requirements)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Create a non-root user for security and set permissions
RUN useradd -m appuser && chown -R appuser:appuser /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Switch to the non-root user
USER appuser

# Expose the port Flask runs on
EXPOSE 5000

# Command to run the application (Using Gunicorn for production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]