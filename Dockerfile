# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2 compilation and other packages
# psycopg2 and other packages with C extensions sometimes require build tools.
# The binary wheels in requirements.txt help, but these are good to have.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Use Gunicorn to run the application, as it is a production-grade WSGI server.
# The `bot:flask_app` argument tells Gunicorn to look for the 'flask_app'
# instance inside your 'bot.py' file.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:$PORT", "bot:flask_app"]
