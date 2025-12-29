"""HWPX IR 컴포넌트 모듈

각 컴포넌트는 reader.py와 writer.py를 포함합니다.
"""

from .text import TextReader, TextWriter
from .paragraph import ParagraphReader, ParagraphWriter
from .table import TableReader, TableWriter
from .image import ImageReader, ImageWriter
from .equation import EquationReader, EquationWriter
from .list import ListReader, ListWriter
from .hyperlink import HyperlinkReader, HyperlinkWriter
from .bookmark import BookmarkReader, BookmarkWriter
from .footnote import FootnoteReader, FootnoteWriter
from .comment import CommentReader, CommentWriter
from .field import FieldReader, FieldWriter
from .toc import TOCReader, TOCWriter
from .caption import CaptionReader, CaptionWriter
from .section import SectionReader, SectionWriter
from .header import HeaderReader, HeaderWriter
from .package import PackageReader, PackageWriter
from .query import HwpxSearcher, HwpxEditor

__all__ = [
    # Text
    "TextReader", "TextWriter",
    # Paragraph
    "ParagraphReader", "ParagraphWriter",
    # Table
    "TableReader", "TableWriter",
    # Image
    "ImageReader", "ImageWriter",
    # Equation
    "EquationReader", "EquationWriter",
    # List
    "ListReader", "ListWriter",
    # Hyperlink
    "HyperlinkReader", "HyperlinkWriter",
    # Bookmark
    "BookmarkReader", "BookmarkWriter",
    # Footnote
    "FootnoteReader", "FootnoteWriter",
    # Comment
    "CommentReader", "CommentWriter",
    # Field
    "FieldReader", "FieldWriter",
    # TOC
    "TOCReader", "TOCWriter",
    # Caption
    "CaptionReader", "CaptionWriter",
    # Section
    "SectionReader", "SectionWriter",
    # Header (header.xml)
    "HeaderReader", "HeaderWriter",
    # Package (content.hpf, settings.xml, version.xml, memoExtended.xml)
    "PackageReader", "PackageWriter",
    # Query (검색, 단락 접근, 편집)
    "HwpxSearcher",
    "HwpxEditor",
]
