#!/usr/bin/env python3
"""Apply reviewed dedupe decisions back into a new QDPX file."""

from __future__ import annotations

import argparse
import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

QDA_NS = "urn:QDA-XML:project:1.0"
NS = {"q": QDA_NS}


@dataclass
class MergeDecision:
    target_guid: str
    source_guid: str
    resolved_name: str


def _find_qdpx_candidates(workspace_root: Path) -> list[Path]:
    qdpx_dir = workspace_root / "qdpx"
    candidates: list[Path] = []
    if qdpx_dir.exists():
        candidates.extend(qdpx_dir.glob("*.qdpx"))
    candidates.extend(workspace_root.glob("*.qdpx"))
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    deduped.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return deduped


def _pick_qdpx_interactive(candidates: list[Path], workspace_root: Path) -> Path:
    if not candidates:
        raise SystemExit("No .qdpx file found in ./qdpx or workspace root.")
    if len(candidates) == 1:
        return candidates[0]

    print("Select a base QDPX file:")
    for idx, candidate in enumerate(candidates, start=1):
        try:
            rel = candidate.resolve().relative_to(workspace_root.resolve())
            display = str(rel)
        except ValueError:
            display = str(candidate)
        print(f"  {idx}) {display}")

    while True:
        raw = input(f"Enter number [1-{len(candidates)}] (blank=1): ").strip()
        if raw == "":
            return candidates[0]
        try:
            selected = int(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if 1 <= selected <= len(candidates):
            return candidates[selected - 1]
        print("Selection out of range.")


def _leaf_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        return cleaned
    if ":" in cleaned:
        return cleaned.split(":")[-1].strip()
    return cleaned


def _parse_review_csv(path: Path) -> list[MergeDecision]:
    if not path.exists():
        raise SystemExit(f"Review CSV not found: {path}")

    decisions: list[MergeDecision] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            decision = (row.get("decision") or "").strip().lower()
            guid_a = (row.get("guid_a") or "").strip().upper()
            guid_b = (row.get("guid_b") or "").strip().upper()
            resolved_name = (row.get("resolved_name") or "").strip()

            if not decision.startswith("merge"):
                continue
            if not guid_a or not guid_b:
                continue

            if decision.startswith("merge:keep_a"):
                decisions.append(
                    MergeDecision(
                        target_guid=guid_a,
                        source_guid=guid_b,
                        resolved_name="",
                    )
                )
            elif decision.startswith("merge:keep_b"):
                decisions.append(
                    MergeDecision(
                        target_guid=guid_b,
                        source_guid=guid_a,
                        resolved_name="",
                    )
                )
            elif decision.startswith("merge:custom"):
                # Keep A by default and apply custom rename to target.
                decisions.append(
                    MergeDecision(
                        target_guid=guid_a,
                        source_guid=guid_b,
                        resolved_name=resolved_name,
                    )
                )

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


def apply_decisions_to_qdpx(base_qdpx: Path, review_csv: Path, out_qdpx: Path) -> None:
    merge_decisions = _parse_review_csv(review_csv)
    if not merge_decisions:
        raise SystemExit("No merge decisions found in review CSV.")

    with zipfile.ZipFile(base_qdpx, "r") as zin:
        try:
            root = ET.fromstring(zin.read("project.qde"))
        except KeyError as exc:
            raise SystemExit("Base QDPX is missing project.qde") from exc

        codes_root = root.find("q:CodeBook/q:Codes", NS)
        if codes_root is None:
            raise SystemExit("project.qde missing CodeBook/Codes")

        code_by_guid, parent_by_guid = _code_parent_index(codes_root)

        remap: dict[str, str] = {}
        rename_by_target: dict[str, str] = {}
        skipped = 0

        def resolve(guid: str) -> str:
            current = guid
            seen: set[str] = set()
            while current in remap and current not in seen:
                seen.add(current)
                current = remap[current]
            return current

        for decision in merge_decisions:
            src = resolve(decision.source_guid)
            tgt = resolve(decision.target_guid)
            if src == tgt:
                continue
            if src not in code_by_guid or tgt not in code_by_guid:
                skipped += 1
                continue

            remap[src] = tgt
            if decision.resolved_name:
                rename_by_target[tgt] = decision.resolved_name

        # Apply code reference remapping.
        refs_changed = 0
        for cref in root.findall(".//q:CodeRef", NS):
            target = cref.attrib.get("targetGUID", "").upper()
            if not target:
                continue
            resolved_target = resolve(target)
            if resolved_target != target:
                cref.attrib["targetGUID"] = resolved_target
                refs_changed += 1

        # Rename surviving targets where requested.
        renamed = 0
        for target_guid, requested_name in rename_by_target.items():
            target_elem = code_by_guid.get(resolve(target_guid))
            if target_elem is None:
                continue
            new_leaf = _leaf_name(requested_name)
            if new_leaf and target_elem.attrib.get("name") != new_leaf:
                target_elem.attrib["name"] = new_leaf
                renamed += 1

        # Remove merged source codes where safe.
        removed = 0
        for source_guid in sorted(remap.keys()):
            source_elem = code_by_guid.get(source_guid)
            parent_elem = parent_by_guid.get(source_guid)
            if source_elem is None or parent_elem is None:
                continue
            if source_elem.findall("q:Code", NS):
                skipped += 1
                continue
            parent_elem.remove(source_elem)
            removed += 1

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
    print(
        "Applied: "
        f"{len(remap)} merge mapping(s), "
        f"{refs_changed} code-ref remap(s), "
        f"{renamed} rename(s), "
        f"{removed} code removal(s), "
        f"{skipped} skipped decision(s)"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply dedupe review CSV to a new QDPX archive.")
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="Base .qdpx file (if omitted, interactive picker is shown)",
    )
    parser.add_argument(
        "--review-csv",
        type=Path,
        default=Path("output/qdpx-dedupe-review.csv"),
        help="Review CSV generated by qdpx-dedupe",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("qdpx/Thesis-deduped.qdpx"),
        help="Output .qdpx path (new file)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(__file__).resolve().parent.parent
    base_qdpx = (
        args.base.resolve()
        if args.base
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )
    if not base_qdpx.exists():
        raise SystemExit(f"Base QDPX not found: {base_qdpx}")

    review_csv = args.review_csv.resolve()
    out_qdpx = args.out.resolve()
    if out_qdpx == base_qdpx:
        raise SystemExit("--out must be a new file; refusing to overwrite base QDPX.")

    apply_decisions_to_qdpx(base_qdpx=base_qdpx, review_csv=review_csv, out_qdpx=out_qdpx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
