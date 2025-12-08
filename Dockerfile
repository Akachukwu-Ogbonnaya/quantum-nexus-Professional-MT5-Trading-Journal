# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose Fly port
EXPOSE 8080

# Start the app using Gunicorn
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8080", "app.app:app"]
