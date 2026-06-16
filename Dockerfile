# Use the official Python slim image
FROM python:3.11.9-slim

# Set environment variables
ENV INSTALL_PATH=/HCMatrix-Chatbot
ENV PYTHONPATH="${INSTALL_PATH}:${PYTHONPATH}"

# Set the working directory
WORKDIR $INSTALL_PATH

# Copy only the requirements file first to leverage Docker caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the application port (assuming Flask or FastAPI)
EXPOSE 5000

# Run the chatbot API
ENTRYPOINT ["python3", "main.py"]
