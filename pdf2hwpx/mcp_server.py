"""pdf2hwpx MCP 서버"""

import asyncio
import base64
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

from pdf2hwpx import Pdf2Hwpx


# MCP 서버 인스턴스
server = Server("pdf2hwpx")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 도구 목록"""
    return [
        Tool(
            name="convert_pdf_to_hwpx",
            description="PDF 파일을 HWPX (한글) 파일로 변환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "변환할 PDF 파일 경로",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 HWPX 파일 경로 (옵션, 기본: PDF 파일명.hwpx)",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pymupdf", "cloud", "openai", "vllm", "mineru"],
                        "description": "PDF 파싱 백엔드 (기본: pymupdf)",
                        "default": "pymupdf",
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="convert_pdf_bytes_to_hwpx",
            description="Base64 인코딩된 PDF 바이트를 HWPX 바이트로 변환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_base64": {
                        "type": "string",
                        "description": "Base64 인코딩된 PDF 데이터",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pymupdf", "cloud", "openai", "vllm", "mineru"],
                        "description": "PDF 파싱 백엔드 (기본: pymupdf)",
                        "default": "pymupdf",
                    },
                },
                "required": ["pdf_base64"],
            },
        ),
        Tool(
            name="search_hwpx",
            description="HWPX 파일에서 텍스트를 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "검색할 HWPX 파일 경로",
                    },
                    "query": {
                        "type": "string",
                        "description": "검색할 텍스트",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "대소문자 구분 여부 (기본: false)",
                        "default": False,
                    },
                },
                "required": ["hwpx_path", "query"],
            },
        ),
        Tool(
            name="edit_hwpx",
            description="HWPX 파일의 텍스트를 수정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "찾을 텍스트",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "바꿀 텍스트",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션, 기본: 원본 파일 덮어쓰기)",
                    },
                },
                "required": ["hwpx_path", "old_text", "new_text"],
            },
        ),
        Tool(
            name="get_hwpx_info",
            description="HWPX 파일의 정보를 가져옵니다 (단락 수, 테이블 수, 이미지 수 등).",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "정보를 가져올 HWPX 파일 경로",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """도구 실행"""
    try:
        if name == "convert_pdf_to_hwpx":
            return await convert_pdf_to_hwpx(arguments)
        elif name == "convert_pdf_bytes_to_hwpx":
            return await convert_pdf_bytes_to_hwpx(arguments)
        elif name == "search_hwpx":
            return await search_hwpx(arguments)
        elif name == "edit_hwpx":
            return await edit_hwpx(arguments)
        elif name == "get_hwpx_info":
            return await get_hwpx_info(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def convert_pdf_to_hwpx(args: dict) -> CallToolResult:
    """PDF를 HWPX로 변환"""
    pdf_path = Path(args["pdf_path"])
    backend = args.get("backend", "pymupdf")
    output_path = args.get("output_path")

    if not pdf_path.exists():
        return CallToolResult(
            content=[TextContent(type="text", text=f"PDF 파일을 찾을 수 없습니다: {pdf_path}")],
            isError=True,
        )

    if output_path is None:
        output_path = pdf_path.with_suffix(".hwpx")
    else:
        output_path = Path(output_path)

    converter = Pdf2Hwpx(backend=backend)
    result = converter.convert(pdf_path, output_path)

    return CallToolResult(
        content=[TextContent(type="text", text=f"변환 완료: {result}")]
    )


async def convert_pdf_bytes_to_hwpx(args: dict) -> CallToolResult:
    """PDF 바이트를 HWPX 바이트로 변환"""
    pdf_base64 = args["pdf_base64"]
    backend = args.get("backend", "pymupdf")

    pdf_bytes = base64.b64decode(pdf_base64)
    converter = Pdf2Hwpx(backend=backend)
    hwpx_bytes = converter.convert_bytes(pdf_bytes)
    hwpx_base64 = base64.b64encode(hwpx_bytes).decode("utf-8")

    return CallToolResult(
        content=[TextContent(type="text", text=hwpx_base64)]
    )


async def search_hwpx(args: dict) -> CallToolResult:
    """HWPX에서 텍스트 검색"""
    import zipfile
    from pdf2hwpx.hwpx_ir.components.query import HwpxSearcher

    hwpx_path = Path(args["hwpx_path"])
    query = args["query"]
    case_sensitive = args.get("case_sensitive", False)

    if not hwpx_path.exists():
        return CallToolResult(
            content=[TextContent(type="text", text=f"HWPX 파일을 찾을 수 없습니다: {hwpx_path}")],
            isError=True,
        )

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        section_xml = zf.read("Contents/section0.xml")

    searcher = HwpxSearcher(section_xml)
    results = searcher.search(query, case_sensitive=case_sensitive)

    if not results:
        return CallToolResult(
            content=[TextContent(type="text", text="검색 결과가 없습니다.")]
        )

    output = f"검색 결과: {len(results)}개\n\n"
    for i, r in enumerate(results[:10]):  # 최대 10개
        output += f"{i+1}. 단락 {r.paragraph_index}: {r.context}\n"

    if len(results) > 10:
        output += f"\n... 외 {len(results) - 10}개"

    return CallToolResult(
        content=[TextContent(type="text", text=output)]
    )


async def edit_hwpx(args: dict) -> CallToolResult:
    """HWPX 텍스트 수정"""
    import zipfile
    from pdf2hwpx.hwpx_ir.components.query import HwpxEditor

    hwpx_path = Path(args["hwpx_path"])
    old_text = args["old_text"]
    new_text = args["new_text"]
    output_path = args.get("output_path", str(hwpx_path))

    if not hwpx_path.exists():
        return CallToolResult(
            content=[TextContent(type="text", text=f"HWPX 파일을 찾을 수 없습니다: {hwpx_path}")],
            isError=True,
        )

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        section_xml = zf.read("Contents/section0.xml")

    editor = HwpxEditor(section_xml)
    replaced = editor.replace_text(old_text, new_text)

    if replaced == 0:
        return CallToolResult(
            content=[TextContent(type="text", text=f"'{old_text}'를 찾을 수 없습니다.")]
        )

    modified_xml = editor.to_bytes()

    # 새 HWPX 파일 생성
    with zipfile.ZipFile(hwpx_path, "r") as zf_in:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.namelist():
                if item == "Contents/section0.xml":
                    zf_out.writestr(item, modified_xml)
                else:
                    zf_out.writestr(item, zf_in.read(item))

    return CallToolResult(
        content=[TextContent(type="text", text=f"{replaced}개 치환됨. 저장됨: {output_path}")]
    )


async def get_hwpx_info(args: dict) -> CallToolResult:
    """HWPX 파일 정보"""
    import zipfile
    from pdf2hwpx.hwpx_ir.components.query import HwpxSearcher

    hwpx_path = Path(args["hwpx_path"])

    if not hwpx_path.exists():
        return CallToolResult(
            content=[TextContent(type="text", text=f"HWPX 파일을 찾을 수 없습니다: {hwpx_path}")],
            isError=True,
        )

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        section_xml = zf.read("Contents/section0.xml")
        file_list = zf.namelist()

    searcher = HwpxSearcher(section_xml)

    info = {
        "파일": str(hwpx_path),
        "단락 수": searcher.get_paragraph_count(),
        "테이블 수": len(searcher.get_tables_info()),
        "이미지 수": len(searcher.get_images_info()),
        "추정 페이지 수": searcher.get_page_count_estimate(),
        "포함된 파일": file_list,
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]
    )


async def main():
    """MCP 서버 실행"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
