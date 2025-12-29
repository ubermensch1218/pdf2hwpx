"""HWPX 문서 프리셋

공식 문서 양식들을 정의합니다.
"""

from .base import DocumentPreset, PresetRegistry
from .official_document import OfficialDocumentPreset

__all__ = [
    "DocumentPreset",
    "PresetRegistry",
    "OfficialDocumentPreset",
]
