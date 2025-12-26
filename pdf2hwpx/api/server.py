"""Cloud Run API 서버"""

import os
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.responses import Response

from pdf2hwpx.core import Pdf2Hwpx
from pdf2hwpx.api.billing import (
    billing_service,
    ApiKeyInfo,
    InvalidApiKeyError,
    QuotaExceededError,
)

app = FastAPI(
    title="pdf2hwpx API",
    description="PDF를 HWPX로 변환하는 API",
    version="0.1.0",
)


async def get_api_key_info(authorization: Optional[str] = Header(None)) -> ApiKeyInfo:
    """API 키 검증 및 정보 조회"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    api_key = authorization[7:]

    try:
        return await billing_service.verify_api_key(api_key)
    except InvalidApiKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/v1/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    api_key_info: ApiKeyInfo = Depends(get_api_key_info),
) -> Response:
    """
    PDF를 HWPX로 변환

    - **file**: PDF 파일
    - **Authorization**: Bearer {api_key}

    Pricing:
    - Free: 50 pages/month
    - Starter: 1,000 pages for 2,000원 (2원/page)
    - Pro: 10,000 pages for 18,000원 (1.8원/page)
    - Business: 100,000 pages for 150,000원 (1.5원/page)
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    pdf_bytes = await file.read()

    # 1. 페이지 수 계산
    pages = billing_service.count_pdf_pages(pdf_bytes)

    # 2. 한도 체크
    try:
        await billing_service.check_quota(api_key_info, pages)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "quota_exceeded",
                "message": str(e),
                "tier": api_key_info.tier.value,
                "used": api_key_info.quota_used,
                "limit": api_key_info.quota_limit,
            },
        )

    # 3. 변환 수행
    try:
        converter = Pdf2Hwpx(
            backend="vllm",
            base_url=os.getenv("INTERNAL_OCR_URL", "http://localhost:8000/v1"),
            api_key=os.getenv("INTERNAL_OCR_KEY", "internal"),
        )

        hwpx_bytes = converter.convert_bytes(pdf_bytes)

        # 4. 사용량 기록
        await billing_service.record_usage(api_key_info.api_key, pages)

        output_filename = file.filename.rsplit(".", 1)[0] + ".hwpx"

        # 응답 헤더에 사용량 정보 포함
        return Response(
            content=hwpx_bytes,
            media_type="application/vnd.hancom.hwpx",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Pages-Used": str(pages),
                "X-Quota-Used": str(api_key_info.quota_used + pages),
                "X-Quota-Limit": str(api_key_info.quota_limit),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.post("/v1/ocr")
async def ocr_pdf(
    file: UploadFile = File(...),
    api_key_info: ApiKeyInfo = Depends(get_api_key_info),
) -> dict:
    """
    PDF에서 OCR 수행 (JSON 결과)

    - **file**: PDF 파일
    - **Authorization**: Bearer {api_key}

    Returns:
        {
          "pages": [
            {
              "page_num": 1,
              "width": 595,
              "height": 842,
              "text_blocks": [...],
              "tables": [...]
            }
          ],
          "metadata": {}
        }
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    pdf_bytes = await file.read()

    # 1. 페이지 수 계산
    pages = billing_service.count_pdf_pages(pdf_bytes)

    # 2. 한도 체크
    try:
        await billing_service.check_quota(api_key_info, pages)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "message": str(e),
                "tier": api_key_info.tier.value,
                "used": api_key_info.quota_used,
                "limit": api_key_info.quota_limit,
            },
        )

    # 3. OCR 수행
    try:
        converter = Pdf2Hwpx(
            backend="vllm",
            base_url=os.getenv("INTERNAL_OCR_URL", "http://localhost:8000/v1"),
        )

        # OCR 결과만 반환 (HWPX 변환 없이)
        from pdf2hwpx.ocr.vllm import VllmOCR

        ocr = VllmOCR(
            base_url=os.getenv("INTERNAL_OCR_URL", "http://localhost:8000/v1"),
            api_key=os.getenv("INTERNAL_OCR_KEY", "internal"),
        )
        ocr_result = ocr.process_bytes(pdf_bytes)

        # 4. 사용량 기록
        await billing_service.record_usage(api_key_info.api_key, pages)

        # 결과 직렬화
        result = {
            "pages": [
                {
                    "page_num": p.page_num,
                    "width": p.width,
                    "height": p.height,
                    "text_blocks": [
                        {
                            "text": b.text,
                            "x": b.x,
                            "y": b.y,
                            "width": b.width,
                            "height": b.height,
                        }
                        for b in p.text_blocks
                    ],
                    "tables": [
                        {
                            "rows": t.rows,
                            "cols": t.cols,
                            "x": t.x,
                            "y": t.y,
                            "width": t.width,
                            "height": t.height,
                            "cells": [
                                {
                                    "text": c.text,
                                    "row": c.row,
                                    "col": c.col,
                                }
                                for c in t.cells
                            ],
                        }
                        for t in p.tables
                    ],
                }
                for p in ocr_result.pages
            ],
            "metadata": ocr_result.metadata,
        }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@app.get("/v1/quota")
async def get_quota(api_key_info: ApiKeyInfo = Depends(get_api_key_info)) -> dict:
    """
    현재 사용량 조회

    - **Authorization**: Bearer {api_key}

    Returns:
        {
          "tier": "pro",
          "used": 5000,
          "limit": 10000,
          "remaining": 5000
        }
    """
    return {
        "tier": api_key_info.tier.value,
        "used": api_key_info.quota_used,
        "limit": api_key_info.quota_limit,
        "remaining": api_key_info.quota_limit - api_key_info.quota_used,
    }


@app.get("/health")
async def health_check() -> dict:
    """헬스 체크"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
