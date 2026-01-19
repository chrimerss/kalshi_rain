FROM mambaorg/micromamba:1.5.1

WORKDIR /app

# Copy environment file
COPY --chown=$MAMBA_USER:$MAMBA_USER backend/environment.yml /app/environment.yml

# Install dependencies
RUN micromamba install -y -n base -f /app/environment.yml && \
    micromamba clean --all --yes

# Activate conda environment in bashrc
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Copy backend source
COPY --chown=$MAMBA_USER:$MAMBA_USER backend /app/backend
# Copy entire project root files if needed (like config expecting root)
# But config.py resolves relative to itself.
# IMPORTANT: backend/src/config.py expects `rain_forecast/backend/src/config.py`
# It does `Path(__file__).resolve().parent.parent.parent` -> tries to go up 3 levels.
# In /app/backend/src/config.py:
# parent -> src
# parent -> backend
# parent -> /app (root)
# So if we mount at /app/backend, it works.

# Create data directory
RUN mkdir -p /app/backend/data

# Entrypoint
CMD ["python", "backend/src/scheduler.py"]
