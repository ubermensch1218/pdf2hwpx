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

## MCP 서버

pdf2hwpx를 MCP(Model Context Protocol) 서버로 사용하면 Claude에서 HWPX 파일을 직접 읽고 편집할 수 있습니다.

### 제공 도구 (22개)

| 카테고리 | 도구 |
|---------|------|
| PDF 변환 | `convert_pdf_to_hwpx`, `convert_pdf_bytes_to_hwpx` |
| 정보 조회 | `get_hwpx_info`, `get_hwpx_text`, `get_hwpx_paragraph`, `get_hwpx_tables`, `get_hwpx_images`, `find_page_breaks` |
| 검색 | `search_hwpx`, `search_hwpx_regex` |
| 텍스트 편집 | `replace_text`, `set_paragraph_text` |
| 단락 관리 | `insert_paragraph`, `delete_paragraph`, `copy_paragraph`, `move_paragraph` |
| 스타일 | `set_paragraph_style`, `set_char_style`, `set_page_break`, `set_column_break` |
| 테이블/이미지 | `insert_table`, `insert_image` |

### Claude Desktop 설정

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 또는 `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "pdf2hwpx": {
      "command": "python",
      "args": ["-m", "pdf2hwpx.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-xxx"
      }
    }
  }
}
```

또는 uv 사용:

```json
{
  "mcpServers": {
    "pdf2hwpx": {
      "command": "uvx",
      "args": ["pdf2hwpx"],
      "env": {
        "OPENAI_API_KEY": "sk-xxx"
      }
    }
  }
}
```

### Claude Code 설정

```bash
claude mcp add pdf2hwpx -- python -m pdf2hwpx.mcp_server
```

### 사용 예시

Claude에서 다음과 같이 사용할 수 있습니다:

```
"test.hwpx 파일의 내용을 보여줘"
→ get_hwpx_text 호출

"'홍길동'을 '김철수'로 바꿔줘"
→ replace_text 호출

"5번 단락 뒤에 새 테이블을 추가해줘"
→ insert_table 호출

"이 마크다운 내용을 test.hwpx의 1번 섹션에 맞춰 작성해줘"
→ get_hwpx_text로 양식 파악 → replace_text/insert_paragraph로 작성
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
├── hwpx_ir/
│   └── components/
│       └── query/
│           ├── searcher.py  # HWPX 검색
│           └── editor.py    # HWPX 편집
├── mcp_server.py        # MCP 서버
└── cli.py               # CLI 인터페이스
```

## 라이선스

이 프로젝트는 [AGPL-3.0](LICENSE) 라이선스를 따릅니다.

- **개인/오픈소스 사용**: 무료
- **상업적 사용**: 소스 공개 의무 또는 Commercial License 구매

Commercial License 문의: contact@room821.im

## 기여

PR 환영합니다! [CONTRIBUTING.md](CONTRIBUTING.md)를 참고해주세요.
