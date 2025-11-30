FROM python:3.10-slim-bookworm

# Install Java for PySpark and other system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

WORKDIR /app

# Copy requirements first to leverage cache
# We copy to a temporary location or directly to where we want it
COPY requirements.txt /app/ts-model/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/ts-model/requirements.txt

# Copy the rest of the application code
COPY . /app/ts-model/

# Expose the API port
EXPOSE 8000

# Set the command to run the API
# We run from /app so that "ts-model/api.py" paths resolve correctly
CMD ["python", "ts-model/api.py"]

