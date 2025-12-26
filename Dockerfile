FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY pyproject.toml .
COPY pdf2hwpx/ pdf2hwpx/

RUN pip install --no-cache-dir ".[api]"

# 포트 설정
ENV PORT=8080
EXPOSE 8080

# 서버 실행
CMD ["python", "-m", "pdf2hwpx.api.server"]
