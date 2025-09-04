FROM python:3.12-alpine3.21

# Update system packages to fix vulnerabilities and add necessary build dependencies
RUN apk update && \
    apk upgrade && \
    apk add --no-cache --virtual .build-deps gcc musl-dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Copy the application
COPY . .

# Create data directory for SQLite
RUN mkdir -p /data

# Set environment variables
ENV PORT=8001

EXPOSE 8001

# Start the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
