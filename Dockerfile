FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install project dependencies (no dev dependencies, no virtual env)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev

# Copy application code
COPY app/ ./app/

# Create data directory
RUN mkdir -p /app/data

EXPOSE 9100

CMD ["poetry", "run", "prod"]
