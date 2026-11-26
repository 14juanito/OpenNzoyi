# NZOYI RL core — stateless microservice, no LLM, no offensive tooling.
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8800

# NZOYI_DATABASE_URL enables PostgreSQL persistence; without it the service
# falls back to an in-memory policy store (dev only).
ENV NZOYI_RL_ALPHA=0.1 \
    NZOYI_RL_GAMMA=0.9 \
    NZOYI_RL_EPSILON=0.2

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8800"]
