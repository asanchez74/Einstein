FROM python:3.14.6-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --gid 10001 einstein \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --no-create-home \
        --shell /usr/sbin/nologin \
        einstein

# OCR facultatif (ADR-0010) : binaires système, aucune bibliothèque Python ajoutée.
ARG INSTALL_OCR=false
RUN if [ "$INSTALL_OCR" = "true" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-fra poppler-utils \
        && rm -rf /var/lib/apt/lists/*; \
    fi

COPY pyproject.toml README.md ./
COPY src ./src

ARG INSTALL_CHATGPT=false
RUN if [ "$INSTALL_CHATGPT" = "true" ]; then \
        python -m pip install --no-cache-dir '.[chatgpt]'; \
    else \
        python -m pip install --no-cache-dir .; \
    fi

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "einstein_core.main:app", "--host", "0.0.0.0", "--port", "8000"]
