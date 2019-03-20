FROM python:3.7-alpine

ENV PYTHONUNBUFFERED=1
RUN pip3 install boto3 requests
COPY jenkins_autoscaler.py /jenkins_autoscaler.py
CMD ["python3", "/jenkins_autoscaler.py"]
