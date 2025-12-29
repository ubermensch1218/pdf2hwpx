"""Package Writer - content.hpf, settings.xml, version.xml, memoExtended.xml 생성"""

from __future__ import annotations

from typing import List
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
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
    "hv": "http://www.hancom.co.kr/hwpml/2011/version",
    "he": "http://www.hancom.co.kr/hwpml/2021/extended",
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:container",
    "odf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


def qname(prefix: str, local: str) -> str:
    """QName 생성"""
    return f"{{{NS[prefix]}}}{local}"


class PackageWriter:
    """HWPX 패키지 파일 생성"""

    # ============================================================
    # content.hpf
    # ============================================================

    def build_content_hpf(self, content_hpf: IrContentHpf) -> bytes:
        """content.hpf 생성 (100% 라운드트립용)"""
        if content_hpf.raw_xml:
            return content_hpf.raw_xml

        root = etree.Element(
            qname("opf", "package"),
            nsmap=NS,
        )
        root.set("version", "")
        root.set("unique-identifier", "")
        root.set("id", "")

        # metadata
        self._build_metadata(root, content_hpf.metadata)

        # manifest
        self._build_manifest(root, content_hpf.manifest_items)

        # spine
        self._build_spine(root, content_hpf.spine_items)

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    def _build_metadata(self, parent: etree._Element, meta: IrDocumentMeta) -> None:
        """메타데이터 생성"""
        metadata = etree.SubElement(parent, qname("opf", "metadata"))

        title = etree.SubElement(metadata, qname("dc", "title"))
        title.text = meta.title

        language = etree.SubElement(metadata, qname("dc", "language"))
        language.text = meta.language

        # meta 태그들
        meta_items = [
            ("creator", "text", meta.creator),
            ("subject", "text", meta.subject),
            ("description", "text", meta.description),
            ("lastsaveby", "text", meta.last_saved_by),
            ("CreatedDate", "text", meta.created_date),
            ("ModifiedDate", "text", meta.modified_date),
            ("date", "text", meta.date),
            ("keyword", "text", meta.keyword),
        ]

        for name, content_type, value in meta_items:
            m = etree.SubElement(metadata, qname("opf", "meta"))
            m.set("name", name)
            m.set("content", content_type)
            m.text = value

    def _build_manifest(self, parent: etree._Element, items: List[IrManifestItem]) -> None:
        """매니페스트 생성"""
        manifest = etree.SubElement(parent, qname("opf", "manifest"))

        for item in items:
            item_el = etree.SubElement(manifest, qname("opf", "item"))
            item_el.set("id", item.id)
            item_el.set("href", item.href)
            item_el.set("media-type", item.media_type)
            if item.is_embedded:
                item_el.set("isEmbeded", "1")

    def _build_spine(self, parent: etree._Element, items: List[IrSpineItem]) -> None:
        """스파인 생성"""
        spine = etree.SubElement(parent, qname("opf", "spine"))

        for item in items:
            itemref = etree.SubElement(spine, qname("opf", "itemref"))
            itemref.set("idref", item.idref)
            itemref.set("linear", "yes" if item.linear else "no")

    # ============================================================
    # settings.xml
    # ============================================================

    def build_settings(self, settings: IrSettings) -> bytes:
        """settings.xml 생성 (100% 라운드트립용)"""
        if settings.raw_xml:
            return settings.raw_xml

        root = etree.Element(
            qname("ha", "HWPApplicationSetting"),
            nsmap={"ha": NS["ha"], "config": NS["config"]},
        )

        if settings.caret_position:
            caret = etree.SubElement(root, qname("ha", "CaretPosition"))
            caret.set("listIDRef", str(settings.caret_position.list_id_ref))
            caret.set("paraIDRef", str(settings.caret_position.para_id_ref))
            caret.set("pos", str(settings.caret_position.pos))

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    # ============================================================
    # version.xml
    # ============================================================

    def build_version(self, version: IrVersion) -> bytes:
        """version.xml 생성 (100% 라운드트립용)"""
        if version.raw_xml:
            return version.raw_xml

        root = etree.Element(
            qname("hv", "HCFVersion"),
            nsmap={"hv": NS["hv"]},
        )
        root.set("tagetApplication", version.target_application)  # typo preserved
        root.set("major", str(version.major))
        root.set("minor", str(version.minor))
        root.set("micro", str(version.micro))
        root.set("buildNumber", str(version.build_number))
        root.set("os", str(version.os))
        root.set("xmlVersion", version.xml_version)
        root.set("application", version.application)
        root.set("appVersion", version.app_version)

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    # ============================================================
    # memoExtended.xml
    # ============================================================

    def build_memo_extended(self, memo_ext: IrMemoExtended) -> bytes:
        """memoExtended.xml 생성 (100% 라운드트립용)"""
        if memo_ext.raw_xml:
            return memo_ext.raw_xml

        root = etree.Element(
            qname("he", "memosEx"),
            nsmap={"he": NS["he"]},
        )

        for memo in memo_ext.memos:
            memo_el = etree.SubElement(root, qname("he", "memo"))
            memo_el.set("id", str(memo.id))
            memo_el.set("parentId", str(memo.parent_id))

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    # ============================================================
    # META-INF/container.xml
    # ============================================================

    def build_container_xml(self, container: IrContainerXml) -> bytes:
        """META-INF/container.xml 생성 (100% 라운드트립용)"""
        if container.raw_xml:
            return container.raw_xml

        root = etree.Element(
            qname("ocf", "container"),
            nsmap={
                "ocf": "urn:oasis:names:tc:opendocument:xmlns:container",
                "hpf": NS["hpf"],
            },
        )

        rootfiles = etree.SubElement(root, qname("ocf", "rootfiles"))
        for rf in container.root_files:
            rootfile = etree.SubElement(rootfiles, qname("ocf", "rootfile"))
            rootfile.set("full-path", rf.full_path)
            rootfile.set("media-type", rf.media_type)

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    # ============================================================
    # META-INF/container.rdf
    # ============================================================

    def build_container_rdf(self, container_rdf: IrContainerRdf) -> bytes:
        """META-INF/container.rdf 생성 (100% 라운드트립용)"""
        if container_rdf.raw_xml:
            return container_rdf.raw_xml

        # 기본 빈 RDF 생성
        root = etree.Element(
            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF",
            nsmap={"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
        )
        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    # ============================================================
    # META-INF/manifest.xml
    # ============================================================

    def build_manifest_xml(self, manifest: IrManifestXml) -> bytes:
        """META-INF/manifest.xml 생성 (100% 라운드트립용)"""
        if manifest.raw_xml:
            return manifest.raw_xml

        root = etree.Element(
            qname("odf", "manifest"),
            nsmap={"odf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"},
        )
        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")
