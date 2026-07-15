FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data
ENV OUTAGE_SWARM_DB=/app/data/outage_swarm.db
EXPOSE 8000
CMD ["uvicorn", "outage_swarm.api:app", "--host", "0.0.0.0", "--port", "8000"]
