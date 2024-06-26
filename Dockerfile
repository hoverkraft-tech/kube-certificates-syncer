FROM python:3.12

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY src/kube-certificates-syncer/ /app/
COPY config.yaml /app/
ENTRYPOINT ["python", "main.py"]
