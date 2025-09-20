# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for cryptography, web3, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install setuptools & wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all bot files
COPY . .

# Expose port (if using webhooks, optional)
EXPOSE 8080

# Start bot
CMD ["python", "bot.py"]
