FROM python:3.9.7-slim
COPY processors/grouper /
COPY commons /commons
RUN pip install -r requirements.txt
ENTRYPOINT ["/bin/sh"]