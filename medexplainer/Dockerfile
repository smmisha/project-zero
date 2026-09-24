# Dockerfile for MedExplainer
# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY medexplainer/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY medexplainer/ .

# Set environment variables
ENV PYTHONPATH=/app
ENV PUBMED_EMAIL=your_email@example.com
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
