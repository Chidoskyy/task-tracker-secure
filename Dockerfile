# Dockerfile: builds the Task Tracker image in two stages
 
# Stage 1, build: install the Python packages into a virtual environment
FROM python:3.14-slim AS build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip
 
# Stage 2, runtime: a clean image with only what the app needs to run
FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip \
    && useradd --create-home --uid 1000 appuser \
    && mkdir /data && chown appuser /data
COPY --from=build /opt/venv /opt/venv
COPY app.py .
ENV PATH="/opt/venv/bin:$PATH" \
    APP_ENV=docker \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8080
CMD ["python", "app.py"]
