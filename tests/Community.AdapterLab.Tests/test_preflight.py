"""Original synthetic PE fixtures: no game executable data is required."""

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("adapter_preflight", SOURCE)
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


def synthetic_pe() -> bytearray:
    """Build a small PE32+ image with original filler and published patterns."""
    data = bytearray(0xA00)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 3, 0, 0, 0, 240, 0x22)
    optional = 0x98
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<II", data, optional + 32, 0x1000, 0x200)
    struct.pack_into("<II", data, optional + 56, 0x4000, 0x200)
    struct.pack_into("<I", data, optional + 108, 16)
    struct.pack_into("<II", data, optional + 136, 0x3000, len(preflight.SIGNATURES) * 12)
    for index, (name, virtual_size, rva, raw_size, raw_offset, flags) in enumerate([
        (b".text", 0x400, 0x1000, 0x400, 0x200, 0x60000020),
        (b".rdata", 0x200, 0x2000, 0x200, 0x600, 0x40000040),
        (b".pdata", 0x200, 0x3000, 0x200, 0x800, 0x40000040),
    ]):
        header = 0x188 + index * 40
        struct.pack_into("<8sIIIIIIHHI", data, header, name, virtual_size, rva, raw_size,
                         raw_offset, 0, 0, 0, 0, flags)
    data[0x200:0x600] = b"\x90" * 0x400
    for index, signature in enumerate(preflight.SIGNATURES.values()):
        code = bytes(0xA5 if token == "?" else int(token, 16) for token in signature.split())
        start = 0x1000 + index * 0x80
        offset = 0x200 + index * 0x80
        data[offset:offset + len(code)] = code
        struct.pack_into("<III", data, 0x800 + index * 12, start, start + 0x40, 0x2000 + index * 4)
    return data


class PreflightTests(unittest.TestCase):
    def inspect(self, data: bytes, allow_fixture: bool = True) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.exe"
            path.write_bytes(data)
            before = path.read_bytes()
            if allow_fixture:
                with patch.object(preflight, "EXPECTED_SHA256", hashlib.sha256(data).hexdigest().upper()):
                    result = preflight.inspect_executable(path)
            else:
                result = preflight.inspect_executable(path)
            self.assertEqual(before, path.read_bytes(), "Read-only preflight altered its input")
            return result

    def test_one_match_at_each_function_start_is_eligible_with_test_allowlist(self):
        result = self.inspect(synthetic_pe())
        self.assertTrue(result["eligible"], result["errors"])
        self.assertEqual("0x8664", result["machine"])
        self.assertEqual([], result["errors"])
        for index, name in enumerate(preflight.SIGNATURES):
            self.assertEqual({"count": 1, "rvas": [0x1000 + index * 0x80]}, result["signatures"][name])

    def test_real_allowlist_rejects_otherwise_valid_fixture_and_retains_counts(self):
        result = self.inspect(synthetic_pe(), allow_fixture=False)
        self.assertFalse(result["eligible"])
        self.assertIn("SHA-256", " ".join(result["errors"]))
        self.assertTrue(all(match["count"] == 1 for match in result["signatures"].values()))

    def test_missing_signature_rejects(self):
        data = synthetic_pe()
        data[0x200] = 0
        result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertEqual(0, result["signatures"]["parse_text"]["count"])

    def test_duplicate_in_nonexecuting_section_also_rejects(self):
        data = synthetic_pe()
        data[0x680:0x680 + 27] = data[0x200:0x200 + 27]
        result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertEqual([0x1000, 0x2080], result["signatures"]["parse_text"]["rvas"])

    def test_only_match_in_nonexecuting_section_rejects(self):
        data = synthetic_pe()
        data[0x680:0x680 + 27] = data[0x200:0x200 + 27]
        data[0x200] = 0
        result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertEqual(1, result["signatures"]["parse_text"]["count"])
        self.assertIn("outside an executable section", " ".join(result["errors"]))

    def test_unique_match_inside_function_is_not_a_function_start(self):
        data = synthetic_pe()
        struct.pack_into("<I", data, 0x80C, 0x1070)
        result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertIn("say: signature is not", " ".join(result["errors"]))

    def test_function_must_contain_entire_signature(self):
        data = synthetic_pe()
        struct.pack_into("<I", data, 0x804, 0x1001)
        result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertIn("parse_text: signature is not", " ".join(result["errors"]))

    def test_scanner_preserves_overlapping_and_wildcard_matches(self):
        self.assertEqual([0, 1], preflight._find_matches(b"AAAA", "41 ? 41"))
        self.assertEqual([0, 2], preflight._find_matches(b"ABABA", "41 42 41"))
        self.assertEqual([0], preflight._find_matches(b"\x40\n\x53", "40 ? 53"))
        self.assertEqual([], preflight._find_matches(b"\x40\x53", "40 ? 53"))

    def test_overlapping_duplicates_fail_the_public_gate(self):
        data = synthetic_pe()
        data[0x400:0x404] = b"AAAA"
        with patch.object(preflight, "SIGNATURES", {"overlap": "41 ? 41"}):
            result = self.inspect(data)
        self.assertFalse(result["eligible"])
        self.assertEqual({"count": 2, "rvas": [0x1200, 0x1201]}, result["signatures"]["overlap"])

    def test_truncation_at_each_structural_boundary_rejects_without_exception(self):
        data = synthetic_pe()
        for length in (0, 2, 63, 0x80, 0x97, 0x187, 0x1FF, 0x5FF, 0x7FF, 0x9FF):
            with self.subTest(length=length):
                result = self.inspect(data[:length])
                self.assertFalse(result["eligible"])
                self.assertTrue(result["errors"])

    def test_bad_header_and_section_bounds_reject(self):
        mutations = [
            (0x3C, "<I", 0xFFFFFFF0),
            (0x84, "<H", 0x14C),
            (0x86, "<H", 0),
            (0x98, "<H", 0x10B),
            (0x98 + 60, "<I", 0x100),
            (0x98 + 108, "<I", 17),
            (0x188 + 8, "<I", 0xFFFFFFFF),
            (0x188 + 20, "<I", 0xFFFFFFF0),
            (0x188 + 20, "<I", 0x100),
            (0x188 + 40 + 12, "<I", 0x1100),
            (0x188 + 40 + 20, "<I", 0x400),
        ]
        for offset, format_, value in mutations:
            with self.subTest(offset=offset, value=value):
                data = synthetic_pe()
                struct.pack_into(format_, data, offset, value)
                self.assertFalse(self.inspect(data)["eligible"])

    def test_bad_exception_metadata_rejects(self):
        mutations = [
            (0x98 + 136, 0),
            (0x98 + 136, 0x31F0),
            (0x98 + 140, 35),
            (0x800, 0x2000),
            (0x804, 0x5000),
            (0x808, 0x5000),
            (0x808, 0x2001),
            (0x80C, 0x1000),
        ]
        for offset, value in mutations:
            with self.subTest(offset=offset, value=value):
                data = synthetic_pe()
                struct.pack_into("<I", data, offset, value)
                result = self.inspect(data)
                self.assertFalse(result["eligible"])
                self.assertTrue(all(match["count"] == 1 for match in result["signatures"].values()))

    def test_unmapped_overlay_does_not_affect_signature_counts(self):
        data = synthetic_pe()
        data.extend(data[0x200:0x220])
        result = self.inspect(data)
        self.assertTrue(result["eligible"], result["errors"])
        self.assertEqual(1, result["signatures"]["parse_text"]["count"])

    def test_uninitialized_virtual_tail_does_not_require_large_allocation(self):
        data = synthetic_pe()
        struct.pack_into("<I", data, 0x98 + 56, 0x80000000)
        struct.pack_into("<I", data, 0x188 + 80 + 8, 0x70000000)
        result = self.inspect(data)
        self.assertTrue(result["eligible"], result["errors"])

    def test_cli_rejects_unknown_executable_as_json_without_launching(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.exe"
            path.write_bytes(synthetic_pe())
            result = subprocess.run([sys.executable, str(SOURCE), "--exe", str(path)],
                                    capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["eligible"])
        self.assertEqual("0x8664", report["machine"])

    def test_missing_path_is_a_closed_diagnostic_result(self):
        with tempfile.TemporaryDirectory() as directory:
            result = preflight.inspect_executable(Path(directory) / "missing.exe")
        self.assertFalse(result["eligible"])
        self.assertIsNone(result["sha256"])
        self.assertEqual(["Executable could not be read."], result["errors"])


if __name__ == "__main__":
    unittest.main()
