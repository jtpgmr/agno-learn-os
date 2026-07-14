FROM python:3.13-slim

# Install uv from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY ./src ./src
COPY test.py ./

CMD ["uv", "run", "test.py"]