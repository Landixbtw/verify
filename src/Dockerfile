# Use the official Python image for your desired version
FROM python:3.11.6

# Set the working directory in the container
WORKDIR /app

# Install system dependencies and MariaDB development files
RUN apt-get update && apt-get install -y \
    build-essential \
    libmariadb-dev \
    libmariadb3 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the .env file into the container (if it's in the same directory)
COPY .env /app/.env

# Run your application
CMD ["python", "main.py"]

