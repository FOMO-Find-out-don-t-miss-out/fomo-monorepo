FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 and GIS
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Use paths relative to the root context
COPY services/harvester-dashboard/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the dashboard code
COPY services/harvester-dashboard /app/services/harvester-dashboard

# Copy the API code (needed for models and geocoder)
COPY services/api /app/services/api

WORKDIR /app/services/harvester-dashboard

ENV PYTHONPATH=/app/services/api:/app/services/harvester-dashboard

EXPOSE 8501

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
