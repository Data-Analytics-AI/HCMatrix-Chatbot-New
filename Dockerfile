
FROM python:3.11.7
RUN apt-get update

ENV INSTALL_PATH /hcm_chatbot
ENV PYTHONPATH="${INSTALL_PATH}:${PYTHONPATH}"

RUN mkdir -p $INSTALL_PATH
WORKDIR $INSTALL_PATH

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python3", "main.py"]
