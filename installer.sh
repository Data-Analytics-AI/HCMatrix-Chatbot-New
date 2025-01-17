# #! /usr/bin/bash

# # To delete the audio resposnse every minute...
# # cd 
# sudo rm -rf HCMatrix-Chatbot
# git clone https://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@github.com/Data-Analytics-AI/HCMatrix-Chatbot.git

# sudo kill -9 $(sudo lsof -t -i :5000)

# cd HCMatrix-Chatbot/

# nohup python3 main.py &
# nohup streamlit run frontend/main.py &


#!/usr/bin/env bash

# Script to update HCMatrix-Chatbot, clean up resources, and restart services.

# Define constants
REPO_URL="https://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@github.com/Data-Analytics-AI/HCMatrix-Chatbot.git"
PROJECT_DIR="HCMatrix-Chatbot"

# Function to terminate processes running on a specific port
terminate_process_on_port() {
    local port=$1
    local pid=$(sudo lsof -t -i :$port)
    if [ -n "$pid" ]; then
        echo "Terminating process on port $port (PID: $pid)..."
        sudo kill -9 $pid
    else
        echo "No process found running on port $port."
    fi
}

# Step 1: Clean up the old project directory
echo "Removing existing project directory..."
sudo rm -rf $PROJECT_DIR

# Step 2: Clone the repository
echo "Cloning repository..."
git clone $REPO_URL

# Step 3: Terminate any processes using specified ports
terminate_process_on_port 5000
terminate_process_on_port 8501

# Step 4: Navigate to the project directory
echo "Navigating to the project directory..."
cd $PROJECT_DIR || { echo "Failed to enter directory: $PROJECT_DIR"; exit 1; }

# Step 5: Start backend and frontend services
echo "Starting backend service..."
nohup python3 main.py > backend.log 2>&1 &
echo "Backend service started."

echo "Starting frontend service..."
nohup streamlit run frontend/main.py > frontend.log 2>&1 &
echo "Frontend service started."

echo "All tasks completed."
