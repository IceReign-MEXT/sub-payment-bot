# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2 compilation
# The binary version of psycopg2 does not require libpq-dev,
# but it's good practice to keep these in case you ever switch.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements file to leverage Docker's layer caching
COPY requirements.txt .

# Install dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Set the default command to run your bot["python", "bot.py"