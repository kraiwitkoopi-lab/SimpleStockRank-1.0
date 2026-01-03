# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the internal port
EXPOSE 8000

# Command to run the application
# Host 0.0.0.0 is required for Docker containers
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
