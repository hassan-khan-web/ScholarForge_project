# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
# build-essential is often needed for compiling Python libraries like lxml
# libgl1 is sometimes needed for image processing libs
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requires.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requires.txt

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI runs on
EXPOSE 5000