from dataclasses import dataclass
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass(frozen=True)
class SheetPreview:
    name: str
    rows: list[list[str]]


def _colnum(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value


def read_xlsx_preview(path: Path, max_rows_per_sheet: int | None = 30) -> list[SheetPreview]:
    previews: list[SheetPreview] = []
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", _NS):
                shared.append("".join(node.text or "" for node in item.findall(".//a:t", _NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("rel:Relationship", _NS)}
        for sheet in workbook.findall("a:sheets/a:sheet", _NS):
            name = sheet.attrib["name"]
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = relmap[rid]
            sheet_path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
            root = ET.fromstring(archive.read(sheet_path))
            rows: list[list[str]] = []
            for row in root.findall("a:sheetData/a:row", _NS):
                cells: list[tuple[int, str]] = []
                has_value = False
                for cell in row.findall("a:c", _NS):
                    value_node = cell.find("a:v", _NS)
                    value = ""
                    if value_node is not None and value_node.text is not None:
                        if cell.attrib.get("t") == "s":
                            index = int(value_node.text)
                            value = shared[index] if index < len(shared) else value_node.text
                        else:
                            value = value_node.text
                    if value:
                        has_value = True
                    cells.append((_colnum(cell.attrib.get("r", "")), value))
                if has_value:
                    dense: list[str] = []
                    last_col = 0
                    for col, value in sorted(cells):
                        while last_col + 1 < col:
                            dense.append("")
                            last_col += 1
                        dense.append(value)
                        last_col = col
                    rows.append(dense)
                    if max_rows_per_sheet is not None and len(rows) >= max_rows_per_sheet:
                        break
            previews.append(SheetPreview(name=name, rows=rows))
    return previews


def read_xlsx(path: Path) -> list[SheetPreview]:
    return read_xlsx_preview(path, max_rows_per_sheet=None)
