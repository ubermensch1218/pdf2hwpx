"""Gemini OCR 백엔드 - Structured Output으로 IR 직접 반환"""

import base64
import io
import os
from pathlib import Path
from typing import Optional, List, Literal

from google import genai
from pydantic import BaseModel, Field
from pdf2image import convert_from_bytes

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table, TableCell


# IR 스키마 정의 (Pydantic)
class BboxSchema(BaseModel):
    """정규화된 바운딩박스 (0-1 범위)"""
    x1: float = Field(description="좌상단 x (0-1)")
    y1: float = Field(description="좌상단 y (0-1)")
    x2: float = Field(description="우하단 x (0-1)")
    y2: float = Field(description="우하단 y (0-1)")


class IrBlockSchema(BaseModel):
    """문서 블록 스키마"""
    type: Literal["paragraph", "table", "heading", "box"] = Field(
        description="블록 타입: paragraph(본문), table(표), heading(제목), box(테두리 있는 박스)"
    )
    bbox: BboxSchema = Field(
        description="정규화된 바운딩박스 (0-1 범위, 이미지 크기 대비 비율)"
    )
    text: Optional[str] = Field(
        default=None,
        description="텍스트 내용 (paragraph, heading, box용)"
    )
    level: Optional[int] = Field(
        default=None,
        description="제목 레벨 1-3 (heading용)"
    )
    rows: Optional[List[List[str]]] = Field(
        default=None,
        description="표 데이터 - 2차원 배열 (table용)"
    )


class PageLayoutSchema(BaseModel):
    """페이지 레이아웃 정보"""
    column_count: int = Field(
        default=1,
        description="컬럼 수 (1=단일 컬럼, 2=2단 컬럼)"
    )


class DocumentIrSchema(BaseModel):
    """문서 IR 스키마"""
    layout: PageLayoutSchema = Field(
        default_factory=PageLayoutSchema,
        description="페이지 레이아웃 정보"
    )
    blocks: List[IrBlockSchema] = Field(
        description="문서 블록 목록"
    )


class GeminiOCR(OCRBackend):
    """Google Gemini 기반 OCR 백엔드

    Structured Output으로 IR 형식을 직접 반환합니다.
    """

    MODELS = {
        "flash": "gemini-2.5-flash-preview-05-20",
        "flash-lite": "gemini-2.5-flash-lite",
        "pro": "gemini-2.5-pro-preview-06-05",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            api_key: Gemini API 키 (없으면 GEMINI_API_KEY 환경변수 사용)
            model: 모델명 (flash, flash-lite, pro 또는 전체 모델명)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY or pass api_key.")

        # 모델 alias 처리
        if model in self.MODELS:
            self.model = self.MODELS[model]
        else:
            self.model = model or self.MODELS["flash-lite"]

        # Gemini 클라이언트 초기화
        self.client = genai.Client(api_key=self.api_key)

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
            img_bytes = img_byte_arr.getvalue()

            # Gemini Vision API 호출 (structured output)
            ir_data = self._call_gemini_vision(img_bytes, image.width, image.height)

            # IR을 PageResult로 변환
            page = self._ir_to_page_result(ir_data, page_num, image.width, image.height)
            pages.append(page)

        return OCRResult(pages=pages, metadata={"model": self.model})

    def _call_gemini_vision(self, img_bytes: bytes, img_width: int = 1000, img_height: int = 1000) -> DocumentIrSchema:
        """Gemini Vision API 호출 (Structured Output)"""

        prompt = """이 문서 이미지를 분석하여 모든 내용을 추출하세요.

레이아웃 분석:
- layout.column_count: 문서의 컬럼 수 (1=단일 컬럼, 2=2단 컬럼)

블록 타입:
- "paragraph": 본문 텍스트
- "heading": 제목 (level: 1=대제목, 2=중제목, 3=소제목)
- "table": 표 (rows에 2차원 배열)
- "box": 테두리 있는 박스/안내문

텍스트 포맷 (마크다운 사용):
- 제목: # 대제목, ## 중제목, ### 소제목
- 줄바꿈: 원본 문서의 줄바꿈을 \\n으로 보존
- 굵은글씨: **텍스트**
- 리스트: 원본 번호/기호 그대로 (①, ②, 가, 나, ○, ● 등)

bbox 규칙:
- 정규화된 좌표 (0-1 범위)
- x1, y1: 좌상단, x2, y2: 우하단"""

        # 이미지 Part 생성
        image_part = {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(img_bytes).decode("utf-8"),
            }
        }

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                {"role": "user", "parts": [{"text": prompt}, image_part]}
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": DocumentIrSchema,
                "max_output_tokens": 65536,
            },
        )

        # Pydantic 모델로 파싱
        try:
            ir_data = DocumentIrSchema.model_validate_json(response.text)
            # bbox 정규화 (픽셀 → 0-1)
            return self._normalize_bbox(ir_data, img_width, img_height)
        except Exception:
            # JSON 파싱 실패시 빈 결과 반환
            return DocumentIrSchema(blocks=[])

    def _normalize_bbox(self, ir_data: DocumentIrSchema, width: int, height: int) -> DocumentIrSchema:
        """bbox를 0-1 범위로 정규화 (픽셀값인 경우)"""
        normalized_blocks = []

        for block in ir_data.blocks:
            bbox = block.bbox
            # 이미 정규화된 경우 (모든 값이 0-1 사이)
            if all(0 <= v <= 1 for v in [bbox.x1, bbox.y1, bbox.x2, bbox.y2]):
                normalized_blocks.append(block)
            else:
                # 픽셀값을 0-1로 정규화
                normalized_bbox = BboxSchema(
                    x1=bbox.x1 / width,
                    y1=bbox.y1 / height,
                    x2=bbox.x2 / width,
                    y2=bbox.y2 / height,
                )
                normalized_blocks.append(IrBlockSchema(
                    type=block.type,
                    bbox=normalized_bbox,
                    text=block.text,
                    level=block.level,
                    rows=block.rows,
                ))

        return DocumentIrSchema(blocks=normalized_blocks)

    def _analyze_layout(self, blocks: List[IrBlockSchema]) -> tuple[List[IrBlockSchema], int]:
        """레이아웃 분석 후 읽기 순서대로 정렬

        1. 콘텐츠 영역 감지 (실제 블록들의 x 범위)
        2. x 중심점 분포로 컬럼 감지
        3. 컬럼별로 그룹화 후 y 순서 정렬
        4. 왼쪽 컬럼 → 오른쪽 컬럼 순서로 병합

        Returns:
            tuple: (정렬된 블록 리스트, 컬럼 수)
        """
        if not blocks:
            return blocks, 1

        # 콘텐츠 영역 계산 (모든 블록의 x 범위)
        all_x1 = [b.bbox.x1 for b in blocks]
        all_x2 = [b.bbox.x2 for b in blocks]
        content_left = min(all_x1)
        content_right = max(all_x2)
        content_width = content_right - content_left
        content_mid = content_left + content_width / 2

        # x 중심점 수집
        x_centers = [(b.bbox.x1 + b.bbox.x2) / 2 for b in blocks]

        # 2컬럼 감지: x 중심점 분포 분석
        # 갭이 큰 곳을 찾아서 컬럼 구분
        sorted_centers = sorted(set(x_centers))
        gaps = []
        for i in range(len(sorted_centers) - 1):
            gap = sorted_centers[i + 1] - sorted_centers[i]
            gaps.append((gap, (sorted_centers[i] + sorted_centers[i + 1]) / 2))

        # 가장 큰 갭을 컬럼 구분선으로 사용 (갭이 콘텐츠 너비의 5% 이상일 때)
        column_separator = content_mid
        is_multi_column = False
        if gaps:
            max_gap = max(gaps, key=lambda x: x[0])
            if max_gap[0] > content_width * 0.05:
                column_separator = max_gap[1]
                is_multi_column = True

        # 블록 분류
        left_blocks = []
        right_blocks = []
        full_width_blocks = []

        for block in blocks:
            block_width = block.bbox.x2 - block.bbox.x1
            x_center = (block.bbox.x1 + block.bbox.x2) / 2

            # 전체 너비 블록 (콘텐츠 너비의 60% 이상)
            if block_width > content_width * 0.6:
                full_width_blocks.append(block)
            # 왼쪽 컬럼
            elif x_center < column_separator:
                left_blocks.append(block)
            # 오른쪽 컬럼
            else:
                right_blocks.append(block)

        # 각 그룹을 y 순서대로 정렬
        full_width_blocks.sort(key=lambda b: b.bbox.y1)
        left_blocks.sort(key=lambda b: b.bbox.y1)
        right_blocks.sort(key=lambda b: b.bbox.y1)

        # 병합
        result = []

        # 상단 전체 너비 블록 (헤더 - y < 0.1)
        top_full = [b for b in full_width_blocks if b.bbox.y1 < 0.1]
        result.extend(top_full)

        # 왼쪽 → 오른쪽
        result.extend(left_blocks)
        result.extend(right_blocks)

        # 하단 전체 너비 블록 (푸터)
        bottom_full = [b for b in full_width_blocks if b.bbox.y1 >= 0.1]
        result.extend(bottom_full)

        # 컬럼 수 판단: 왼쪽과 오른쪽 둘 다 3개 이상 블록이 있으면 2컬럼
        detected_col_count = 2 if (is_multi_column and len(left_blocks) >= 3 and len(right_blocks) >= 3) else 1

        return result, detected_col_count

    def _ir_to_page_result(self, ir_data: DocumentIrSchema, page_num: int, width: int, height: int) -> PageResult:
        """IR 데이터를 PageResult로 변환"""
        text_blocks: List[TextBlock] = []
        tables: List[Table] = []

        # 레이아웃 분석 및 정렬 (컬럼 수 자동 감지)
        sorted_blocks, detected_col_count = self._analyze_layout(ir_data.blocks)

        # 컬럼 수: bbox 분석 결과 사용 (Gemini 응답보다 신뢰성 높음)
        column_count = detected_col_count

        for block in sorted_blocks:
            # bbox를 실제 좌표로 변환
            x = block.bbox.x1 * width
            y = block.bbox.y1 * height
            w = (block.bbox.x2 - block.bbox.x1) * width
            h = (block.bbox.y2 - block.bbox.y1) * height

            if block.type == "table" and block.rows:
                table = self._create_table(block.rows, y, width, h)
                tables.append(table)
            else:
                text = block.text or ""
                if text:
                    # heading level 결정
                    heading_level = 0
                    if block.type == "heading" and block.level:
                        heading_level = block.level

                    text_blocks.append(
                        TextBlock(
                            text=text.strip(),
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            is_box=(block.type == "box"),
                            heading_level=heading_level,
                        )
                    )

        return PageResult(
            page_num=page_num,
            width=float(width),
            height=float(height),
            text_blocks=text_blocks,
            tables=tables,
            images=[],
            column_count=column_count,
        )

    def _create_table(self, rows: List[List[str]], y_pos: float, page_width: int, height: float = None) -> Table:
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
        table_height = height if height else len(rows) * 20.0

        return Table(
            rows=len(rows),
            cols=num_cols,
            x=0.0,
            y=y_pos,
            width=float(page_width),
            height=table_height,
            cells=cells,
        )
