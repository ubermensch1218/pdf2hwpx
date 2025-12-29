"""Package Reader - content.hpf, settings.xml, version.xml, memoExtended.xml 파싱"""

from __future__ import annotations

from typing import List, Optional
from lxml import etree

from pdf2hwpx.hwpx_ir.models import (
    IrContentHpf, IrDocumentMeta, IrManifestItem, IrSpineItem,
    IrSettings, IrCaretPosition,
    IrVersion,
    IrMemoExtended, IrMemoItem,
    IrContainerXml, IrRootFile, IrContainerRdf, IrManifestXml,
)


# 네임스페이스
NS = {
    "opf": "http://www.idpf.org/2007/opf/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "hv": "http://www.hancom.co.kr/hwpml/2011/version",
    "he": "http://www.hancom.co.kr/hwpml/2021/extended",
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:container",
    "odf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


class PackageReader:
    """HWPX 패키지 파일 파싱"""

    # ============================================================
    # content.hpf
    # ============================================================

    def parse_content_hpf(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrContentHpf:
        """content.hpf 파싱"""
        root = etree.fromstring(xml_bytes)

        # metadata
        metadata_el = root.find("opf:metadata", NS)
        metadata = self._parse_metadata(metadata_el) if metadata_el is not None else IrDocumentMeta()

        # manifest
        manifest_el = root.find("opf:manifest", NS)
        manifest_items = self._parse_manifest(manifest_el) if manifest_el is not None else []

        # spine
        spine_el = root.find("opf:spine", NS)
        spine_items = self._parse_spine(spine_el) if spine_el is not None else []

        return IrContentHpf(
            metadata=metadata,
            manifest_items=manifest_items,
            spine_items=spine_items,
            raw_xml=xml_bytes if preserve_raw else None,
        )

    def _parse_metadata(self, metadata_el: etree._Element) -> IrDocumentMeta:
        """메타데이터 파싱"""
        title_el = metadata_el.find("dc:title", NS)
        title = title_el.text or "" if title_el is not None else ""

        lang_el = metadata_el.find("dc:language", NS)
        language = lang_el.text or "ko" if lang_el is not None else "ko"

        # meta 태그들
        creator = ""
        subject = ""
        description = ""
        last_saved_by = ""
        created_date = ""
        modified_date = ""
        date = ""
        keyword = ""

        for meta in metadata_el.findall("opf:meta", NS):
            name = meta.get("name", "")
            content = meta.get("content", "")
            if name == "creator":
                creator = content
            elif name == "subject":
                subject = content
            elif name == "description":
                description = content
            elif name == "lastsaveby":
                last_saved_by = content
            elif name == "CreatedDate":
                created_date = content
            elif name == "ModifiedDate":
                modified_date = content
            elif name == "date":
                date = content
            elif name == "keyword":
                keyword = content

        return IrDocumentMeta(
            title=title,
            language=language,
            creator=creator,
            subject=subject,
            description=description,
            last_saved_by=last_saved_by,
            created_date=created_date,
            modified_date=modified_date,
            date=date,
            keyword=keyword,
        )

    def _parse_manifest(self, manifest_el: etree._Element) -> List[IrManifestItem]:
        """매니페스트 파싱"""
        items = []
        for item in manifest_el.findall("opf:item", NS):
            item_id = item.get("id", "")
            href = item.get("href", "")
            media_type = item.get("media-type", "")
            is_embedded = item.get("isEmbeded", "0") == "1"

            items.append(IrManifestItem(
                id=item_id,
                href=href,
                media_type=media_type,
                is_embedded=is_embedded,
            ))
        return items

    def _parse_spine(self, spine_el: etree._Element) -> List[IrSpineItem]:
        """스파인 파싱"""
        items = []
        for itemref in spine_el.findall("opf:itemref", NS):
            idref = itemref.get("idref", "")
            linear = itemref.get("linear", "yes") == "yes"
            items.append(IrSpineItem(idref=idref, linear=linear))
        return items

    # ============================================================
    # settings.xml
    # ============================================================

    def parse_settings(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrSettings:
        """settings.xml 파싱"""
        root = etree.fromstring(xml_bytes)

        # CaretPosition
        caret_el = root.find("ha:CaretPosition", NS)
        caret_position = None
        if caret_el is not None:
            caret_position = IrCaretPosition(
                list_id_ref=int(caret_el.get("listIDRef", "0")),
                para_id_ref=int(caret_el.get("paraIDRef", "0")),
                pos=int(caret_el.get("pos", "0")),
            )

        return IrSettings(
            caret_position=caret_position,
            raw_xml=xml_bytes if preserve_raw else None,
        )

    # ============================================================
    # version.xml
    # ============================================================

    def parse_version(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrVersion:
        """version.xml 파싱"""
        root = etree.fromstring(xml_bytes)

        return IrVersion(
            target_application=root.get("tagetApplication", "WORDPROCESSOR"),  # typo in HWPX spec
            major=int(root.get("major", "5")),
            minor=int(root.get("minor", "1")),
            micro=int(root.get("micro", "1")),
            build_number=int(root.get("buildNumber", "0")),
            os=int(root.get("os", "10")),
            xml_version=root.get("xmlVersion", "1.5"),
            application=root.get("application", "Hancom Office Hangul"),
            app_version=root.get("appVersion", ""),
            raw_xml=xml_bytes if preserve_raw else None,
        )

    # ============================================================
    # memoExtended.xml
    # ============================================================

    def parse_memo_extended(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrMemoExtended:
        """memoExtended.xml 파싱"""
        root = etree.fromstring(xml_bytes)

        memos = []
        for memo in root.findall("he:memo", NS):
            memo_id = int(memo.get("id", "0"))
            parent_id = int(memo.get("parentId", "0"))
            memos.append(IrMemoItem(id=memo_id, parent_id=parent_id))

        return IrMemoExtended(
            memos=memos,
            raw_xml=xml_bytes if preserve_raw else None,
        )

    # ============================================================
    # META-INF/container.xml
    # ============================================================

    def parse_container_xml(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrContainerXml:
        """META-INF/container.xml 파싱"""
        root = etree.fromstring(xml_bytes)

        root_files = []
        rootfiles_el = root.find("ocf:rootfiles", NS)
        if rootfiles_el is not None:
            for rf in rootfiles_el.findall("ocf:rootfile", NS):
                full_path = rf.get("full-path", "")
                media_type = rf.get("media-type", "")
                root_files.append(IrRootFile(full_path=full_path, media_type=media_type))

        return IrContainerXml(
            root_files=root_files,
            raw_xml=xml_bytes if preserve_raw else None,
        )

    # ============================================================
    # META-INF/container.rdf
    # ============================================================

    def parse_container_rdf(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrContainerRdf:
        """META-INF/container.rdf 파싱 (raw_xml만 보존)"""
        return IrContainerRdf(raw_xml=xml_bytes if preserve_raw else None)

    # ============================================================
    # META-INF/manifest.xml
    # ============================================================

    def parse_manifest_xml(self, xml_bytes: bytes, preserve_raw: bool = True) -> IrManifestXml:
        """META-INF/manifest.xml 파싱 (raw_xml만 보존)"""
        return IrManifestXml(raw_xml=xml_bytes if preserve_raw else None)
