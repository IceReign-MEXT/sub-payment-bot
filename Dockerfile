# Use an official Python base image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy requirements first (to leverage Docker cache)
COPY requirements.txt .

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libffi-dev curl && \
    pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Expose port if needed (not required for Telegram bot)
# EXPOSE 8443

# Run the bot
CMD ["python", "bot.py"]
