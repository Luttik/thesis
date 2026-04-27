#!/usr/bin/env python3
"""Apply category-assignment decisions back into a new QDPX file."""

from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}


@dataclass
class CategoryDecision:
    code_guid: str
    parent_guid: str


def _parse_review_csv(path: Path) -> list[CategoryDecision]:
    if not path.exists():
        raise SystemExit(f"Category review CSV not found: {path}")

    decisions: list[CategoryDecision] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            status = (row.get("status") or "").strip().lower()
            if status != "assigned":
                continue

            code_guid = (row.get("code_guid") or "").strip().upper()
            parent_guid = (row.get("selected_parent_guid") or "").strip().upper()
            if not code_guid or not parent_guid:
                continue

            decisions.append(CategoryDecision(code_guid=code_guid, parent_guid=parent_guid))
    return decisions


def _code_parent_index(
    codes_root: ET.Element,
) -> tuple[dict[str, ET.Element], dict[str, ET.Element]]:
    code_by_guid: dict[str, ET.Element] = {}
    parent_by_guid: dict[str, ET.Element] = {}

    def walk(parent: ET.Element) -> None:
        for code in parent.findall("q:Code", NS):
            guid = code.attrib.get("guid", "").upper()
            if guid:
                code_by_guid[guid] = code
                parent_by_guid[guid] = parent
            walk(code)

    walk(codes_root)
    return code_by_guid, parent_by_guid


def apply_category_decisions_to_qdpx(base_qdpx: Path, review_csv: Path, out_qdpx: Path) -> None:
    decisions = _parse_review_csv(review_csv)
    if not decisions:
        raise SystemExit("No assigned category decisions found in review CSV.")

    with zipfile.ZipFile(base_qdpx, "r") as zin:
        try:
            root = ET.fromstring(zin.read("project.qde"))
        except KeyError as exc:
            raise SystemExit("Base QDPX is missing project.qde") from exc

        codes_root = root.find("q:CodeBook/q:Codes", NS)
        if codes_root is None:
            raise SystemExit("project.qde missing CodeBook/Codes")

        code_by_guid, parent_by_guid = _code_parent_index(codes_root)
        moved = 0
        skipped = 0

        for decision in decisions:
            code_elem = code_by_guid.get(decision.code_guid)
            target_parent = code_by_guid.get(decision.parent_guid)
            current_parent = parent_by_guid.get(decision.code_guid)
            if code_elem is None or target_parent is None or current_parent is None:
                skipped += 1
                continue
            if decision.code_guid == decision.parent_guid:
                skipped += 1
                continue

            # Only allow assignment to top-level parent categories.
            parent_of_target = parent_by_guid.get(decision.parent_guid)
            if parent_of_target is not codes_root:
                skipped += 1
                continue

            if current_parent is target_parent:
                continue

            try:
                current_parent.remove(code_elem)
                target_parent.append(code_elem)
                parent_by_guid[decision.code_guid] = target_parent
                moved += 1
            except ValueError:
                skipped += 1

        xml_data = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        out_qdpx.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_qdpx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "project.qde":
                    data = xml_data
                zout.writestr(info, data)

    print(f"Base QDPX: {base_qdpx}")
    print(f"Review CSV: {review_csv}")
    print(f"Output QDPX: {out_qdpx}")
    print(f"Applied: {moved} category assignment(s), {skipped} skipped decision(s)")
