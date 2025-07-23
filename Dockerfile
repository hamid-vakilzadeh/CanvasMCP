FROM python:3.13

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv
RUN uv sync --frozen

COPY src/ ./src/

EXPOSE 3000

CMD ["uv", "run", "python", "src/index.py"]