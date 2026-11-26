# nzoyi-api — orchestrateur HTTP + agents + outils + gates.
# Les binaires offensifs (nmap, nuclei, …) ne sont PAS inclus : les wrappers
# dégradent proprement s'ils sont absents. Installez-les dans l'image ou montez
# un volume outillage selon votre lab.
FROM python:3.13-slim

WORKDIR /app

# Dépendances : API + Alembic (migrations lancées au démarrage).
COPY nzoyi-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    "uvicorn[standard]>=0.29" alembic>=1.13 sqlalchemy>=2.0 psycopg2-binary>=2.9

COPY nzoyi-api /app/nzoyi-api
COPY db /app/db

WORKDIR /app/nzoyi-api
EXPOSE 8000

# NZOYI_CORE_URL  -> microservice RL (sinon repli in-process indisponible ici)
# NZOYI_DATABASE_URL -> PostgreSQL partagé
ENV PYTHONUNBUFFERED=1

# Applique les migrations puis démarre l'API.
CMD sh -c "cd /app/db && alembic upgrade head || echo '[warn] migrations non appliquées'; \
           cd /app/nzoyi-api && uvicorn server:app --host 0.0.0.0 --port 8000"
