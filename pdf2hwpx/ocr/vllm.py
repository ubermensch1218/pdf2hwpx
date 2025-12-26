"""vLLM 서버 OCR 백엔드 - BBOX + OCR"""

import base64
import io
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx
from pdf2image import convert_from_bytes

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table, TableCell


class VllmOCR(OCRBackend):
    """vLLM 서버 백엔드 (OpenAI-compatible API with Vision)"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.getenv("VLLM_API_KEY", "dummy")
        self.model = model or os.getenv("VLLM_MODEL", "gemini-2.5-flash-lite")

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 OCR 수행"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 OCR 수행"""
        # 1. PDF를 페이지별 이미지로 변환
        images = convert_from_bytes(pdf_bytes, dpi=200)

        pages = []
        for page_num, image in enumerate(images, start=1):
            # 2. 이미지를 base64로 인코딩
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            # 3. vLLM Vision API 호출
            ocr_data = self._call_vision_api(img_base64, image.width, image.height)

            # 4. OCR 결과를 PageResult로 변환
            page = self._parse_ocr_result(ocr_data, page_num, image.width, image.height)
            pages.append(page)

        return OCRResult(pages=pages, metadata={})

    def _call_vision_api(self, img_base64: str, width: int, height: int) -> Dict[str, Any]:
        """vLLM Vision API 호출 (BBOX + OCR)"""

        # Vision OCR을 위한 프롬프트
        prompt = """Analyze this document image and extract all text elements with their bounding boxes.

Return a JSON response with this exact structure:
{
  "elements": [
    {
      "type": "text" | "table",
      "bbox": [x1, y1, x2, y2],  # in pixels
      "text": "extracted text content",
      "rows": [["cell1", "cell2"], ["cell3", "cell4"]]  // for tables only
    }
  ]
}

Rules:
- Bbox coordinates must be in pixels (0-0 is top-left)
- Extract all visible text including headers, paragraphs
- For tables, extract cell content in row-major order
- Return valid JSON only, no markdown"""

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
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        # 응답 파싱
        content = data["choices"][0]["message"]["content"]

        # JSON 파싱 (markdown 코드블록 제거)
        import json
        import re

        # ```json ... ``` 제거
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # 중괄호 추출
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

        return json.loads(content)

    def _parse_ocr_result(self, ocr_data: Dict, page_num: int, width: int, height: int) -> PageResult:
        """OCR 결과를 PageResult로 변환"""
        text_blocks: List[TextBlock] = []
        tables: List[Table] = []

        elements = ocr_data.get("elements", [])

        for elem in elements:
            elem_type = elem.get("type", "text")
            bbox = elem.get("bbox", [])

            if elem_type == "table":
                # 테이블 파싱
                rows = elem.get("rows", [])
                if rows:
                    table = self._parse_table(rows, bbox, width, height)
                    tables.append(table)
            else:
                # 텍스트 블록 파싱
                text = elem.get("text", "")
                if text and len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox
                    text_blocks.append(
                        TextBlock(
                            text=text,
                            x=float(x1),
                            y=float(y1),
                            width=float(x2 - x1),
                            height=float(y2 - y1),
                        )
                    )

        return PageResult(
            page_num=page_num,
            width=float(width),
            height=float(height),
            text_blocks=text_blocks,
            tables=tables,
            images=[],
        )

    def _parse_table(self, rows: List[List[str]], bbox: List, page_width: int, page_height: int) -> Table:
        """테이블 데이터 파싱"""
        cells: List[TableCell] = []

        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_text in enumerate(row_data):
                cells.append(
                    TableCell(
                        text=str(cell_text),
                        row=row_idx,
                        col=col_idx,
                        rowspan=1,
                        colspan=1,
                    )
                )

        x1, y1, x2, y2 = bbox if len(bbox) >= 4 else [0, 0, page_width, page_height]

        return Table(
            rows=len(rows),
            cols=len(rows[0]) if rows else 0,
            x=float(x1),
            y=float(y1),
            width=float(x2 - x1) if len(bbox) >= 4 else float(page_width),
            height=float(y2 - y1) if len(bbox) >= 4 else 100.0,
            cells=cells,
        )
