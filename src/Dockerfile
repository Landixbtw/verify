
# Use the official Python image for your desired version
FROM python:3.11.6

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install development tools and libraries
RUN apt-get update && apt-get install -y build-essential

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Copy the .env file into the container (if it's in the same directory)
COPY .env /app/.env

# Expose the port your app runs on (if applicable)
# EXPOSE 8080

# Run your application
CMD ["python", "main.py"]

