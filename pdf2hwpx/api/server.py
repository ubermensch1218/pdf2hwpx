"""Cloud Run API 서버"""

import os
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.responses import Response

from pdf2hwpx.core import Pdf2Hwpx

app = FastAPI(
    title="pdf2hwpx API",
    description="PDF를 HWPX로 변환하는 API",
    version="0.1.0",
)


async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """API 키 검증"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    api_key = authorization[7:]

    # TODO: 실제 API 키 검증 로직
    # - DB에서 키 확인
    # - 사용량 체크
    # - Rate limiting

    return api_key


@app.post("/v1/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
) -> Response:
    """
    PDF를 HWPX로 변환

    - **file**: PDF 파일
    - **Authorization**: Bearer {api_key}
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    pdf_bytes = await file.read()

    # 내부 OCR 서버 사용 (vLLM)
    converter = Pdf2Hwpx(
        backend="vllm",
        base_url=os.getenv("INTERNAL_OCR_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("INTERNAL_OCR_KEY", "internal"),
    )

    hwpx_bytes = converter.convert_bytes(pdf_bytes)

    output_filename = file.filename.rsplit(".", 1)[0] + ".hwpx"

    return Response(
        content=hwpx_bytes,
        media_type="application/vnd.hancom.hwpx",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"'
        },
    )


@app.post("/v1/ocr")
async def ocr_pdf(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    PDF에서 OCR 수행 (JSON 결과)

    - **file**: PDF 파일
    - **Authorization**: Bearer {api_key}
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")

    pdf_bytes = await file.read()

    # TODO: OCR 수행 및 결과 반환
    # 내부 vLLM 서버로 OCR 수행

    return {
        "pages": [],
        "metadata": {},
    }


@app.get("/health")
async def health_check() -> dict:
    """헬스 체크"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
