from __future__ import annotations

import os
import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree
from PIL import Image

from pdf2hwpx.hwpx_ir.writer import HwpxIrWriter, HwpxBinaryItem
from pdf2hwpx.hwpx_ir.models import (
    IrBlock, IrDocument, IrImage, IrParagraph, IrTextRun
)


@dataclass(frozen=True)
class PdfMetadataToHwpxResult:
    hwpx_bytes: bytes


class PdfMetadataToHwpxConverter:
    """Convert PDF metadata JSON to HWPX document.

    Expected input:
    {
      "title": "Document Title",
      "elements": [
        {
          "id": 0,
          "label": "text",
          "ocr_texts": ["텍스트 1", "텍스트 2"],
          "related_formulas": [
            {"latex": "\\frac{1}{2}"}
          ]
        },
        {
          "id": 1,
          "label": "image",
          "image_file": "element-0.png",
          "bbox": [x1, y1, x2, y2]
        }
      ],
      "image_paths": {
        "element-0.png": "/path/to/element-0.png"
      },
      "page_size": {
        "width": 595,
        "height": 842
      }
    }
    """

    # HWPX unit conversion
    # 1 inch = 72 DPI = 1440 HWPUNIT
    HWPUNIT_PER_INCH = 1440
    MM_PER_INCH = 25.4

    def __init__(self, template_hwpx_path: str):
        self._writer = HwpxIrWriter(template_hwpx_path=template_hwpx_path)
        self._next_nested_picture_id = 2000000000

    def convert(self, data: dict, image_dir: Optional[str] = None) -> PdfMetadataToHwpxResult:
        """Convert PDF metadata to HWPX.

        Args:
            data: Metadata dict with title, elements, and optional page_size
            image_dir: Directory containing image files (optional)
        """

        if not isinstance(data, dict):
            raise ValueError("Input must be a dict")

        title = data.get("title", "PDF Document")
        if not isinstance(title, str):
            raise ValueError("'title' must be a string")

        elements = data.get("elements", [])
        if not isinstance(elements, list):
            raise ValueError("'elements' must be an array")

        page_size = data.get("page_size", {"width": 595, "height": 842})
        page_width = page_size.get("width", 595)
        page_height = page_size.get("height", 842)

        # Load images from disk
        image_paths = data.get("image_paths", {})
        binary_items, filename_to_id, id_to_org_size = self._load_images(image_paths, image_dir)

        # Build IR blocks
        blocks: list[IrBlock] = []

        # Add title
        blocks.append(IrBlock(
            type="paragraph",
            paragraph=IrParagraph(inlines=[IrTextRun(text=title)])
        ))

        # Process each element
        for elem in elements:
            if not isinstance(elem, dict):
                continue

            label = elem.get("label", "text").lower()

            # Add text blocks
            if label == "text":
                ocr_texts = elem.get("ocr_texts", [])
                for text in ocr_texts:
                    if isinstance(text, str) and text.strip():
                        blocks.append(IrBlock(
                            type="paragraph",
                            paragraph=IrParagraph(inlines=[IrTextRun(text=text)])
                        ))

                # Add related formulas
                formulas = elem.get("related_formulas", [])
                for formula in formulas:
                    if isinstance(formula, dict):
                        latex = formula.get("latex", "")
                        if latex:
                            # Render formula as text for now
                            blocks.append(IrBlock(
                                type="paragraph",
                                paragraph=IrParagraph(inlines=[IrTextRun(text=f"[식] {latex}")])
                            ))

            # Add image blocks with size calculation
            elif label == "image":
                image_file = elem.get("image_file")
                # Look up the sanitized ID using the filename
                image_id = filename_to_id.get(image_file)
                
                if image_id and image_id in binary_items:
                    # Get bbox for sizing (optional)
                    bbox = elem.get("bbox")
                    width_hwpunit, height_hwpunit = self._calculate_image_size(
                        bbox, page_width, page_height
                    )

                    org_sz = id_to_org_size.get(image_id)
                    org_w = org_sz[0] if org_sz else None
                    org_h = org_sz[1] if org_sz else None

                    image = IrImage(
                        image_id=image_id,
                        width_hwpunit=width_hwpunit,
                        height_hwpunit=height_hwpunit,
                        org_width=org_w,
                        org_height=org_h,
                        treat_as_char=False  # Floating by default
                    )
                    blocks.append(IrBlock(type="image", image=image))

        # Build document
        doc = IrDocument(blocks=blocks)
        hwpx_bytes = self._writer.write(doc, binary_items=binary_items)

        return PdfMetadataToHwpxResult(hwpx_bytes=hwpx_bytes)

    def _calculate_image_size(
        self,
        bbox: Optional[List[float]],
        page_width: float,
        page_height: float
    ) -> tuple[int, int]:
        """Calculate image size in HWPUNIT based on bbox or page size.

        Args:
            bbox: [x1, y1, x2, y2] in PDF points (1/72 inch)
            page_width: Page width in PDF points
            page_height: Page height in PDF points

        Returns:
            (width_hwpunit, height_hwpunit)
        """
        # 페이지 마진 (양쪽 각각 약 10mm = 28.35pt)
        MARGIN_PT = 28.35

        if bbox and len(bbox) >= 4:
            # Use bbox dimensions
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            width_pt = x2 - x1
            height_pt = y2 - y1
        else:
            # Use full page dimensions with margins
            width_pt = page_width - (2 * MARGIN_PT)
            height_pt = page_height - (2 * MARGIN_PT)

        # Convert from PDF points to HWPUNIT
        # PDF uses 72 DPI, HWPUNIT is 1440 per inch
        width_hwpunit = int(width_pt * (self.HWPUNIT_PER_INCH / 72))
        height_hwpunit = int(height_pt * (self.HWPUNIT_PER_INCH / 72))

        return width_hwpunit, height_hwpunit

    def _load_images(
        self,
        image_paths: Dict[str, str],
        image_dir: Optional[str] = None
    ) -> Tuple[Dict[str, HwpxBinaryItem], Dict[str, str], Dict[str, Tuple[int, int]]]:
        """Load images from disk paths.

        Returns:
            (binary_items, filename_to_id, id_to_org_size)
        """
        binary_items: Dict[str, HwpxBinaryItem] = {}
        filename_to_id: Dict[str, str] = {}
        id_to_org_size: Dict[str, Tuple[int, int]] = {}
        
        sorted_keys = sorted(image_paths.keys()) # sort for deterministic IDs
        for idx, image_filename in enumerate(sorted_keys):
            image_path = image_paths[image_filename]
            
            if not isinstance(image_path, str):
                continue

            # Add image_dir prefix if provided
            if image_dir:
                full_path = str(Path(image_dir) / image_path)
            else:
                full_path = image_path

            try:
                with open(full_path, "rb") as f:
                    image_data = f.read()

                # Generate a safe, unique ID for the binary item
                # Format: imgX (e.g. img1) - matching mid.hwpx style
                new_id = f"img{idx+1}"
                
                real_filename = Path(full_path).name
                
                # Check extension for zip filename
                ext = os.path.splitext(real_filename)[1]
                if not ext:
                    ext = ".png"
                safe_filename = f"{new_id}{ext}"
                
                binary_items[new_id] = HwpxBinaryItem(
                    id=new_id,
                    filename=safe_filename,
                    data=image_data
                )
                filename_to_id[image_filename] = new_id
                
                # Calculate Original Size
                with Image.open(io.BytesIO(image_data)) as img:
                    # 1 pixel approx 75 HWPUnits
                    org_w = int(img.width * 75)
                    org_h = int(img.height * 75)
                    id_to_org_size[new_id] = (org_w, org_h)

            except Exception as e:
                # Log but continue with other images
                print(f"Warning: Could not load image '{full_path}': {e}")
                # Fallback for size if image loaded but size calc failed (though unlikely if read failed)
                # If read failed, we didn't add to binary_items, so no ID to map in org_size.
                pass

        return binary_items, filename_to_id, id_to_org_size
