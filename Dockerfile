# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all bot files
COPY . .

# Expose port if using webhooks (optional)
EXPOSE 8080

# Start the bot
CMD ["python", "bot.py"]
