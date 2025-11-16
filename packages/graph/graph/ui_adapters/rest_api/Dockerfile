FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "ui_adapters.rest_api.server:app", "--host", "0.0.0.0", "--port", "8000"]