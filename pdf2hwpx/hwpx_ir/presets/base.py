"""프리셋 기본 클래스"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrMargin,
    IrPageMargin,
    IrPageNumber,
    IrParagraph,
    IrSection,
    IrTable,
    IrTableCell,
    IrTextRun,
)


@dataclass
class PresetField:
    """프리셋 필드 정의"""
    name: str  # 필드 이름 (예: "recipient", "title")
    label: str  # 표시 레이블 (예: "수신", "제목")
    required: bool = True
    default_value: str = ""
    max_length: Optional[int] = None


class DocumentPreset(ABC):
    """문서 프리셋 기본 클래스"""

    # 프리셋 메타데이터
    preset_id: str = ""
    preset_name: str = ""
    description: str = ""

    @classmethod
    @abstractmethod
    def get_fields(cls) -> List[PresetField]:
        """프리셋에서 필요한 필드 목록"""
        pass

    @classmethod
    @abstractmethod
    def get_page_settings(cls) -> IrSection:
        """페이지 설정 반환"""
        pass

    @classmethod
    @abstractmethod
    def build_document(cls, field_values: Dict[str, str]) -> IrDocument:
        """필드 값을 받아 문서 생성"""
        pass

    @classmethod
    def validate_fields(cls, field_values: Dict[str, str]) -> List[str]:
        """필드 유효성 검사. 오류 메시지 목록 반환."""
        errors = []
        for field in cls.get_fields():
            value = field_values.get(field.name, "")
            if field.required and not value:
                errors.append(f"'{field.label}' 필드는 필수입니다.")
            if field.max_length and len(value) > field.max_length:
                errors.append(f"'{field.label}' 필드는 {field.max_length}자 이하여야 합니다.")
        return errors


class PresetRegistry:
    """프리셋 레지스트리"""

    _presets: Dict[str, Type[DocumentPreset]] = {}

    @classmethod
    def register(cls, preset_class: Type[DocumentPreset]) -> Type[DocumentPreset]:
        """프리셋 등록 데코레이터"""
        cls._presets[preset_class.preset_id] = preset_class
        return preset_class

    @classmethod
    def get(cls, preset_id: str) -> Optional[Type[DocumentPreset]]:
        """프리셋 ID로 프리셋 클래스 반환"""
        return cls._presets.get(preset_id)

    @classmethod
    def list_all(cls) -> List[Type[DocumentPreset]]:
        """모든 프리셋 목록"""
        return list(cls._presets.values())

    @classmethod
    def get_by_name(cls, name: str) -> Optional[Type[DocumentPreset]]:
        """프리셋 이름으로 검색"""
        for preset in cls._presets.values():
            if preset.preset_name == name:
                return preset
        return None
