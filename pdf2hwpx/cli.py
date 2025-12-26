"""pdf2hwpx CLI"""

import argparse
import sys
from pathlib import Path

from pdf2hwpx import Pdf2Hwpx


def main():
    parser = argparse.ArgumentParser(
        description="PDF를 HWPX로 변환",
        prog="pdf2hwpx",
    )
    parser.add_argument("input", help="입력 PDF 파일")
    parser.add_argument("-o", "--output", help="출력 HWPX 파일")
    parser.add_argument(
        "--backend",
        choices=["cloud", "openai", "vllm"],
        default="cloud",
        help="OCR 백엔드 (기본: cloud)",
    )
    parser.add_argument("--api-key", help="API 키")
    parser.add_argument("--base-url", help="vLLM 서버 URL")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".hwpx")

    try:
        converter = Pdf2Hwpx(
            backend=args.backend,
            api_key=args.api_key,
            base_url=args.base_url,
        )
        result = converter.convert(input_path, output_path)
        print(f"Converted: {result}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
