# Multi-stage Dockerfile for Binance Spark Processor
# Base: Python 3.12 with OpenJDK 17 (required for PySpark)

FROM python:3.12-slim

# Install system dependencies including Java
RUN apt-get update && apt-get install -y \
    default-jdk-headless \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Java environment variables
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH=$PATH:$JAVA_HOME/bin

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py .
COPY websocket_client.py .
COPY spark_processor.py .
COPY s3_writer.py .
COPY main.py .

# Create logs and spark-events directories
RUN mkdir -p /app/logs /app/logs/spark-events

# Set Spark home (PySpark includes Spark binaries)
ENV SPARK_HOME=/usr/local/lib/python3.12/site-packages/pyspark

# Environment variables for Spark configuration
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Expose Spark UI port
EXPOSE 4040

# Expose volume mount point for logs
VOLUME ["/app/logs"]

# Set entrypoint
ENTRYPOINT ["python", "main.py"]

# Health check (optional)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python main.py" || exit 1

