FROM python:3.13

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv
RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--frozen", "--no-dev", "python", "src/local.py"]
