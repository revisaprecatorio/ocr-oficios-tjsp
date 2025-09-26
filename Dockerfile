FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for web API
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy application code
COPY app/ ./app/
COPY run_sistema.py .
COPY schema.sql .
COPY api.py .

# Create directories
RUN mkdir -p /app/Processos /app/logs /app/web

# Create simple web interface
RUN echo '<!DOCTYPE html>\n\
<html>\n\
<head>\n\
    <title>Sistema OCR - Ofícios TJSP</title>\n\
    <meta charset="utf-8">\n\
</head>\n\
<body>\n\
    <h1>🏛️ Sistema OCR - Ofícios Requisitórios TJSP</h1>\n\
    <p>Sistema funcionando corretamente!</p>\n\
    <p>Status: <span style="color: green;">✅ Ativo</span></p>\n\
</body>\n\
</html>' > /app/web/index.html

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port for Traefik
EXPOSE 8000

# Default command - API server para compatibilidade com Traefik
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
