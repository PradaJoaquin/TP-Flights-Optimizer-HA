FROM python:3.9.7-slim
COPY health_checker /
COPY commons /commons
RUN pip install -r requirements.txt
ENTRYPOINT ["/bin/sh"]