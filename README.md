# pdf2hwpx

PDF를 HWPX(한글 문서)로 변환하는 오픈소스 라이브러리

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## 특징

- **PDF → HWPX 원스톱 변환**: OCR과 HWPX 변환을 한 번에
- **다양한 OCR 백엔드 지원**: OpenAI Vision, vLLM
- **한국어 최적화**: 한글 문서에 특화된 레이아웃 보존
- **오픈소스**: AGPL-3.0 라이선스

## 설치

```bash
pip install pdf2hwpx
```

## 빠른 시작

### OpenAI Vision 사용

```python
from pdf2hwpx import Pdf2Hwpx

converter = Pdf2Hwpx(
    backend="openai",
    api_key="sk-xxx"
)
converter.convert("input.pdf", "output.hwpx")
```

### 자체 vLLM 서버 사용 (BBOX + OCR)

vLLM 서버를 사용하면 **BBOX(위치 정보) + OCR**을 한 번에 수행합니다.

```python
from pdf2hwpx import Pdf2Hwpx

# gemini-2.5-flash-lite 등 Vision 모델이 필요합니다
converter = Pdf2Hwpx(
    backend="vllm",
    base_url="http://localhost:8000/v1",
    model="gemini-2.5-flash-lite"  # 선택사항
)
converter.convert("input.pdf", "output.hwpx")
```

**vLLM 서버 실행 예시**:
```bash
# vLLM으로 gemini-2.5-flash-lite 서비스 시작
vllm serve google/gemini-2.0-flash-exp \
  --port 8000 \
  --chat-template template.jinja \
  --max-model-len 4096
```

**참고**: vLLM 백엔드는 PDF를 이미지로 변환 후 Vision API로 분석합니다. `poppler`가 필요합니다:
```bash
# macOS
brew install poppler

# Ubuntu/Debian
apt-get install poppler-utils
```

## CLI 사용

```bash
# OpenAI 백엔드
pdf2hwpx input.pdf -o output.hwpx --backend openai --api-key sk-xxx

# vLLM 백엔드
pdf2hwpx input.pdf -o output.hwpx --backend vllm --base-url http://localhost:8000/v1
```

## 아키텍처

```
pdf2hwpx/
├── ocr/
│   ├── base.py          # OCR 인터페이스
│   ├── openai.py        # OpenAI Vision
│   └── vllm.py          # vLLM 서버
├── converter/
│   └── hwpx_builder.py  # HWPX 변환 로직
└── cli.py               # CLI 인터페이스
```

## 라이선스

이 프로젝트는 [AGPL-3.0](LICENSE) 라이선스를 따릅니다.

- **개인/오픈소스 사용**: 무료
- **상업적 사용**: 소스 공개 의무 또는 Commercial License 구매

Commercial License 문의: contact@room821.im

## 기여

PR 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해주세요.
