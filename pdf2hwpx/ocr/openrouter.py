"""OpenRouter OCR 백엔드 - Structured Output으로 IR 직접 반환"""

import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx
from pdf2image import convert_from_bytes

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table, TableCell


# IR 출력을 위한 JSON Schema
IR_SCHEMA = {
    "type": "object",
    "properties": {
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["paragraph", "table", "heading"]
                    },
                    "text": {"type": "string"},
                    "level": {"type": "integer"},
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4
                    }
                },
                "required": ["type"]
            }
        }
    },
    "required": ["blocks"]
}


class OpenRouterOCR(OCRBackend):
    """OpenRouter API 기반 OCR 백엔드

    다양한 Vision LLM 모델을 지원하며 structured output으로 IR 형식을 직접 반환합니다.
    """

    # 추천 모델들
    MODELS = {
        "gemini-flash": "google/gemini-2.0-flash-001",
        "gemini-pro": "google/gemini-2.5-pro-preview",
        "claude-sonnet": "anthropic/claude-sonnet-4",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Args:
            api_key: OpenRouter API 키 (없으면 OPENROUTER_API_KEY 환경변수 사용)
            model: 모델명 (없으면 gemini-flash 사용)
            base_url: API URL (기본: https://openrouter.ai/api/v1)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY or pass api_key.")

        # 모델 alias 처리
        if model in self.MODELS:
            self.model = self.MODELS[model]
        else:
            self.model = model or self.MODELS["gemini-flash"]

        self.base_url = base_url or "https://openrouter.ai/api/v1"

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 OCR 수행"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 OCR 수행"""
        images = convert_from_bytes(pdf_bytes, dpi=200)

        pages = []
        for page_num, image in enumerate(images, start=1):
            # 이미지를 base64로 인코딩
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            # Vision API 호출
            ir_data = self._call_vision_api(img_base64, image.width, image.height)

            # IR을 PageResult로 변환
            page = self._ir_to_page_result(ir_data, page_num, image.width, image.height)
            pages.append(page)

        return OCRResult(pages=pages, metadata={"model": self.model})

    def _call_vision_api(self, img_base64: str, width: int, height: int) -> Dict[str, Any]:
        """OpenRouter Vision API 호출"""

        prompt = """이 문서 이미지를 분석하여 모든 내용을 추출하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{
  "blocks": [
    {"type": "heading", "text": "제목 텍스트", "level": 1},
    {"type": "paragraph", "text": "본문 텍스트"},
    {"type": "table", "rows": [["셀1", "셀2"], ["셀3", "셀4"]]}
  ]
}

규칙:
- type은 "paragraph", "table", "heading" 중 하나
- heading은 level 포함 (1=큰제목, 2=중제목, 3=소제목)
- table은 rows에 2차원 배열로 셀 내용
- 문서 순서대로 추출
- JSON만 반환, 다른 텍스트 없이"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 8192,
            "temperature": 0.1,
        }

        # Structured output 지원 모델은 response_format 사용
        if "gemini" in self.model or "gpt-4" in self.model:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "document_ir",
                    "schema": IR_SCHEMA,
                    "strict": True,
                }
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/room821/pdf2hwpx",
        }

        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return self._parse_json_response(content)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """JSON 응답 파싱 (코드블록 제거)"""
        # ```json ... ``` 제거
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # 중괄호 추출
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"blocks": [{"type": "paragraph", "text": content}]}

    def _ir_to_page_result(self, ir_data: Dict, page_num: int, width: int, height: int) -> PageResult:
        """IR 데이터를 PageResult로 변환"""
        text_blocks: List[TextBlock] = []
        tables: List[Table] = []

        blocks = ir_data.get("blocks", [])
        y_pos = 0.0
        line_height = 20.0

        for block in blocks:
            block_type = block.get("type", "paragraph")

            if block_type == "table":
                rows = block.get("rows", [])
                if rows:
                    table = self._create_table(rows, y_pos, width)
                    tables.append(table)
                    y_pos += len(rows) * line_height
            else:
                text = block.get("text", "")
                if text:
                    # heading은 텍스트로 처리
                    if block_type == "heading":
                        level = block.get("level", 1)
                        # 레벨에 따라 크기 조정 (나중에 스타일로 처리 가능)
                        text = text.strip()

                    text_blocks.append(
                        TextBlock(
                            text=text,
                            x=0.0,
                            y=y_pos,
                            width=float(width),
                            height=line_height,
                        )
                    )
                    y_pos += line_height

        return PageResult(
            page_num=page_num,
            width=float(width),
            height=float(height),
            text_blocks=text_blocks,
            tables=tables,
            images=[],
        )

    def _create_table(self, rows: List[List[str]], y_pos: float, page_width: int) -> Table:
        """테이블 생성"""
        cells: List[TableCell] = []

        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_text in enumerate(row_data):
                cells.append(
                    TableCell(
                        text=str(cell_text) if cell_text else "",
                        row=row_idx,
                        col=col_idx,
                        rowspan=1,
                        colspan=1,
                    )
                )

        num_cols = len(rows[0]) if rows else 1

        return Table(
            rows=len(rows),
            cols=num_cols,
            x=0.0,
            y=y_pos,
            width=float(page_width),
            height=len(rows) * 20.0,
            cells=cells,
        )
