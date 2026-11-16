# deploy/Dockerfile — réplica del notario GUS
FROM python:3.12-slim

# Banderas de build reproducible
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY src/ /app/src/

# Usuario no privilegiado
RUN useradd --system --create-home --shell /usr/sbin/nologin gus
USER gus

EXPOSE 8080
CMD ["python3", "-m", "gerarion.notary_service"]
