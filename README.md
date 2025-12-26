# pdf2hwpx

PDF를 HWPX(한글 문서)로 변환하는 오픈소스 라이브러리

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## 특징

- **PDF → HWPX 원스톱 변환**: OCR과 HWPX 변환을 한 번에
- **다양한 OCR 백엔드 지원**: Cloud API(기본), OpenAI Vision, vLLM
- **한국어 최적화**: 한글 문서에 특화된 레이아웃 보존
- **오픈소스**: AGPL-3.0 라이선스

## 설치

```bash
pip install pdf2hwpx
```

## 빠른 시작

### Cloud API 사용 (기본, 권장)

```python
from pdf2hwpx import Pdf2Hwpx

converter = Pdf2Hwpx(api_key="your-api-key")
converter.convert("input.pdf", "output.hwpx")
```

### OpenAI Vision 사용

```python
from pdf2hwpx import Pdf2Hwpx

converter = Pdf2Hwpx(
    backend="openai",
    api_key="sk-xxx"
)
converter.convert("input.pdf", "output.hwpx")
```

### 자체 vLLM 서버 사용

```python
from pdf2hwpx import Pdf2Hwpx

converter = Pdf2Hwpx(
    backend="vllm",
    base_url="http://localhost:8000/v1",
    api_key="your-key"
)
converter.convert("input.pdf", "output.hwpx")
```

## CLI 사용

```bash
# Cloud API (기본)
pdf2hwpx input.pdf -o output.hwpx --api-key YOUR_KEY

# OpenAI 백엔드
pdf2hwpx input.pdf -o output.hwpx --backend openai --api-key sk-xxx

# vLLM 백엔드
pdf2hwpx input.pdf -o output.hwpx --backend vllm --base-url http://localhost:8000/v1
```

## OCR 백엔드 비교

| 백엔드 | 비용 | 특징 |
|--------|------|------|
| **cloud** (기본) | ~2원/페이지 | 가장 쉬움, HWPX 변환 포함 |
| openai | ~50원/페이지 | OpenAI Vision API |
| vllm | 자체 비용 | 직접 서버 운영 필요 |

## 가격

| 티어 | 페이지 | 가격 | 페이지당 |
|------|--------|------|----------|
| Free | 50 | 0원 | - |
| Starter | 1,000 | 2,000원 | 2원 |
| Pro | 10,000 | 18,000원 | 1.8원 |
| Business | 100,000 | 150,000원 | 1.5원 |

## 아키텍처

```
pdf2hwpx/
├── ocr/
│   ├── base.py          # OCR 인터페이스
│   ├── cloud.py         # Cloud API (기본)
│   ├── openai.py        # OpenAI Vision
│   └── vllm.py          # vLLM 서버
├── converter/
│   └── hwpx_builder.py  # HWPX 변환 로직
├── api/
│   └── server.py        # Cloud Run API 서버
└── cli.py               # CLI 인터페이스
```

## API 서버 (Cloud Run)

```bash
# 로컬 실행
docker build -t pdf2hwpx-api .
docker run -p 8080:8080 pdf2hwpx-api

# API 호출
curl -X POST https://api.pdf2hwpx.com/convert \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@input.pdf" \
  -o output.hwpx
```

## 라이선스

이 프로젝트는 [AGPL-3.0](LICENSE) 라이선스를 따릅니다.

- **개인/오픈소스 사용**: 무료
- **상업적 사용**: 소스 공개 의무 또는 Commercial License 구매

Commercial License 문의: contact@pdf2hwpx.com

## 기여

PR 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해주세요.
