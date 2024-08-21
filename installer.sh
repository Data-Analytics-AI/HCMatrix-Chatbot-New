#! /usr/bin/bash

# To delete the audio resposnse every minute...
# cd 
sudo rm -rf HCMatrix-Chatbot
git clone https://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@github.com/Data-Analytics-AI/HCMatrix-Chatbot.git

sudo kill -9 $(sudo lsof -t -i :5000)
sudo kill -9 $(sudo lsof -t -i :8501)

cd HCMatrix-Chatbot/

nohup python3 main.py &
nohup streamlit run frontend/main.py &
