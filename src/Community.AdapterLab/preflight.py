"""Read-only executable checks for the T-04.2 candidate experiment.

Eligibility permits an experiment; it does not establish runtime compatibility.
This module uses no game libraries, starts no process, and emits no game bytes.
PE layout: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
Unwind records: https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct


EXPECTED_SHA256 = "B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB"

# Maintainer-published signatures, NMS.py b41bf9e6fdff1c833b77d805bb0c8da555c4ced4.
# Only these signature strings are used; no upstream implementation is imported.
SIGNATURES = {
    "parse_text": "40 55 53 57 48 8D AC 24 ? ? ? ? B8 ? ? ? ? E8 ? ? ? ? 48 2B E0 80 3A",
    "say": "40 53 48 81 EC ? ? ? ? F3 0F 10 05",
}


@dataclass(frozen=True)
class _Section:
    rva: int
    size: int
    raw_offset: int
    raw_size: int
    executable: bool


def _require_range(offset: int, size: int, limit: int, label: str) -> None:
    if offset < 0 or size < 0 or offset > limit or size > limit - offset:
        raise ValueError(f"{label} is outside its containing data.")


def _find_matches(data: bytes, signature: str) -> list[int]:
    """Find every match, including overlaps, using a fixed-byte search anchor."""
    pattern = [None if token in ("?", "??") else int(token, 16)
               for token in signature.split()]
    if not pattern or any(value is not None and not 0 <= value <= 255 for value in pattern):
        raise ValueError("Invalid signature pattern.")
    runs: list[tuple[int, bytes]] = []
    index = 0
    while index < len(pattern):
        if pattern[index] is None:
            index += 1
            continue
        start = index
        while index < len(pattern) and pattern[index] is not None:
            index += 1
        runs.append((start, bytes(pattern[start:index])))
    if not runs:
        raise ValueError("A signature needs at least one fixed byte.")
    anchor_offset, anchor = max(runs, key=lambda run: len(run[1]))
    fixed = [(offset, value) for offset, value in enumerate(pattern) if value is not None]
    matches = []
    search_offset = 0
    while (found := data.find(anchor, search_offset)) >= 0:
        start = found - anchor_offset
        if 0 <= start <= len(data) - len(pattern):
            if all(data[start + offset] == value for offset, value in fixed):
                matches.append(start)
        search_offset = found + 1
    return matches


def _parse_pe(data: bytes, report: dict) -> tuple[list[_Section], int, int]:
    _require_range(0, 64, len(data), "DOS header")
    if data[:2] != b"MZ":
        raise ValueError("Missing DOS signature.")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset < 64:
        raise ValueError("PE header overlaps the DOS header.")
    _require_range(pe_offset, 24, len(data), "PE header")
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("Missing PE signature.")
    machine, section_count = struct.unpack_from("<HH", data, pe_offset + 4)
    report["machine"] = f"0x{machine:04x}"
    if machine != 0x8664:
        raise ValueError("The candidate experiment requires x64 (0x8664).")
    if not 1 <= section_count <= 96:
        raise ValueError("Invalid PE section count.")
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    _require_range(optional_offset, optional_size, len(data), "Optional header")
    if optional_size < 112 or struct.unpack_from("<H", data, optional_offset)[0] != 0x20B:
        raise ValueError("The candidate experiment requires a PE32+ optional header.")
    image_size, header_size = struct.unpack_from("<II", data, optional_offset + 56)
    directory_count = struct.unpack_from("<I", data, optional_offset + 108)[0]
    if directory_count < 4 or directory_count > (optional_size - 112) // 8:
        raise ValueError("Missing or truncated exception directory declaration.")
    exception_rva, exception_size = struct.unpack_from("<II", data, optional_offset + 136)
    section_table = optional_offset + optional_size
    _require_range(section_table, section_count * 40, len(data), "Section table")
    if not section_table + section_count * 40 <= header_size <= len(data):
        raise ValueError("Invalid PE header size.")
    if image_size <= header_size:
        raise ValueError("Invalid PE image size.")
    sections = []
    for index in range(section_count):
        offset = section_table + index * 40
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        characteristics = struct.unpack_from("<I", data, offset + 36)[0]
        # Include raw alignment padding as well as the zero-filled virtual tail.
        mapped_size = max(virtual_size, raw_size)
        if not mapped_size or rva < header_size:
            raise ValueError("Empty section or section overlapping image headers.")
        _require_range(rva, mapped_size, image_size, "Mapped section")
        if raw_size:
            if raw_offset < header_size:
                raise ValueError("Section raw data overlaps image headers.")
            _require_range(raw_offset, raw_size, len(data), "Section raw data")
        section = _Section(rva, mapped_size, raw_offset, raw_size, bool(characteristics & 0x20000000))
        for previous in sections:
            if rva < previous.rva + previous.size and previous.rva < rva + mapped_size:
                raise ValueError("Overlapping mapped sections.")
            if raw_size and previous.raw_size:
                if raw_offset < previous.raw_offset + previous.raw_size and previous.raw_offset < raw_offset + raw_size:
                    raise ValueError("Overlapping section raw data.")
        sections.append(section)
    return sections, exception_rva, exception_size


def _file_offset(sections: list[_Section], rva: int, size: int) -> int:
    for section in sections:
        relative = rva - section.rva
        if 0 <= relative and relative + size <= section.raw_size:
            return section.raw_offset + relative
    raise ValueError("Exception metadata points outside initialized section data.")


def _runtime_functions(data: bytes, sections: list[_Section], rva: int, size: int) -> dict[int, int]:
    if not rva or not size or size % 12:
        raise ValueError("Missing or malformed x64 exception table.")
    offset = _file_offset(sections, rva, size)
    functions = {}
    previous_start = -1
    for entry in range(offset, offset + size, 12):
        start, end, unwind_rva = struct.unpack_from("<III", data, entry)
        if start <= previous_start or end <= start:
            raise ValueError("Unsorted or invalid runtime function entry.")
        if not any(section.executable and section.rva <= start < end <= section.rva + section.size
                   for section in sections):
            raise ValueError("Runtime function is outside an executable section.")
        if not unwind_rva or unwind_rva % 4:
            raise ValueError("Invalid runtime function unwind address.")
        _file_offset(sections, unwind_rva, 4)
        functions[start] = end
        previous_start = start
    return functions


def inspect_executable(path: Path) -> dict:
    """Return a fail-closed report; never launch, load, or alter the executable."""
    report = {
        "sha256": None,
        "machine": None,
        "signatures": {name: {"count": 0, "rvas": []} for name in SIGNATURES},
        "eligible": False,
        "errors": [],
    }
    try:
        data = path.read_bytes()
    except OSError:
        report["errors"].append("Executable could not be read.")
        return report
    report["sha256"] = hashlib.sha256(data).hexdigest().upper()
    if report["sha256"] != EXPECTED_SHA256:
        report["errors"].append("Executable SHA-256 is outside the candidate allowlist.")
    try:
        sections, exception_rva, exception_size = _parse_pe(data, report)
        for name, signature in SIGNATURES.items():
            length = len(signature.split())
            rvas = []
            for section in sections:
                section_data = data[section.raw_offset:section.raw_offset + section.raw_size]
                # All selected patterns contain fixed nonzero bytes. A wholly
                # zero-filled tail cannot match; only its boundary is needed.
                section_data += b"\0" * min(section.size - section.raw_size, length - 1)
                rvas.extend(section.rva + offset for offset in _find_matches(section_data, signature))
            report["signatures"][name] = {"count": len(rvas), "rvas": sorted(rvas)}
            if len(rvas) != 1:
                report["errors"].append(f"{name}: expected exactly one signature match; found {len(rvas)}.")
            elif not any(section.executable and section.rva <= rvas[0] < section.rva + section.size
                         for section in sections):
                report["errors"].append(f"{name}: signature is outside an executable section.")
        functions = _runtime_functions(data, sections, exception_rva, exception_size)
        for name, signature in SIGNATURES.items():
            matches = report["signatures"][name]["rvas"]
            if len(matches) == 1:
                rva = matches[0]
                if rva not in functions or functions[rva] < rva + len(signature.split()):
                    report["errors"].append(f"{name}: signature is not a complete runtime function entry prefix.")
    except (ValueError, struct.error) as error:
        report["errors"].append(str(error))
    report["eligible"] = not report["errors"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, type=Path, help="Owned executable to inspect without launching")
    arguments = parser.parse_args()
    report = inspect_executable(arguments.exe)
    print(json.dumps(report, indent=2))
    return 0 if report["eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
