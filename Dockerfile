# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (to leverage Docker cache)
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all bot files
COPY . .

# Expose port (optional, for webhook monitoring)
EXPOSE 8080

# Start the bot
CMD ["python", "bot.py"]
