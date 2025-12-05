# ================================
# Base Image (Python 3.12 — required for pandas/numpy)
# ================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# ================================
# Install system-level dependencies
# ================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ================================
# Install Python dependencies
# ================================
COPY requirements.txt /code/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ================================
# Copy project
# ================================
COPY . /code/

# ================================
# Collect static files
# ================================
RUN python manage.py collectstatic --no-input || true

# ================================
# Expose port (Fly.io reads PORT env)
# ================================
EXPOSE 8000

# ================================
# Start the Django app via Gunicorn
# ================================
CMD ["gunicorn", "rokumeals.wsgi:application", "--bind", "0.0.0.0:8000"]
