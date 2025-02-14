# Use the official Python image
FROM python:3.11.9

# Update system packages and install only required dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Set environment variables
ENV INSTALL_PATH /HCMatrix-Chatbot
ENV PYTHONPATH="${INSTALL_PATH}:${PYTHONPATH}"

# Set the working directory
WORKDIR $INSTALL_PATH

# Copy only requirements first to leverage Docker caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the application port (if running a Flask or FastAPI app)
EXPOSE 5000

# Run the chatbot API
CMD ["python3", "main.py"]
