"""Original synthetic memory and PE fixtures; no game files or imports."""

from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
import native_state


BASE = 0x180000000
OWNER = 0x200000000


class Memory:
    def __init__(self, base=BASE, owner=OWNER, state=None, pending=bytes(16)):
        self.base = base
        self.calls = []
        self.block = bytearray(0x30)
        struct.pack_into("<Q", self.block, 0, base + native_state.APPVIEW_RVA if state is None else state)
        self.block[8:24] = pending
        struct.pack_into("<Q", self.block, 0x28, owner)
        self.receiver = owner + native_state.CHAT_OFFSET

    def read(self, address, size):
        self.calls.append((address, size))
        if address == self.base + native_state.SINGLETON_RVA + 0x10 and size == 0x30:
            return bytes(self.block)
        if address == self.receiver and size == 16:
            return bytes(16)
        raise RuntimeError("Reader address must never reach the caller's diagnostic.")


def synthetic_pe():
    """Tiny original file whose sparse virtual layout includes the fixed globals."""
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 3, 0, 0, 0, 240, 0x22)
    struct.pack_into("<H", data, 0x98, 0x20B)
    struct.pack_into("<II", data, 0x98 + 56, native_state.IMAGE_SIZE, 0x200)
    struct.pack_into("<I", data, 0x98 + 108, 16)
    struct.pack_into("<II", data, 0x98 + 136, 0x2000, 12)
    for index, (name, rva, virtual_size, raw_offset, flags) in enumerate([
        (b".text", 0x1000, 0x200, 0x200, 0x60000020),
        (b".rdata", 0x2000, 0x200, 0x400, 0x40000040),
        (b".data", native_state.SINGLETON_RVA, 0x2000, 0x600, 0xC0000040),
    ]):
        struct.pack_into("<8sIIIIIIHHI", data, 0x188 + index * 40,
                         name, virtual_size, rva, 0x200, raw_offset, 0, 0, 0, 0, flags)
    data[0x200:0x210] = b"ORIGINAL CODE!!!"
    data[0x400:0x410] = b"ORIGINAL TABLE!!"
    # Slice assignment must preserve the exact requested fixture span length.
    assert len(data) == 0x800
    spans = tuple(native_state.GuardSpan(name, rva, 16,
                  hashlib.sha256(data[offset:offset + 16]).hexdigest().upper())
                  for name, rva, offset in (("code", 0x1000, 0x200), ("table", 0x2000, 0x400)))
    return data, spans


class NativeStateTests(unittest.TestCase):
    def test_fresh_sample_and_pointer_free_summary(self):
        memory = Memory()
        state = native_state.NativeState(BASE, memory.read)
        sample = state.sample()
        self.assertEqual(OWNER + native_state.CHAT_OFFSET, sample.receiver)
        self.assertEqual({"playable": True, "pending_clear": True, "owner_valid": True}, sample.summary())
        self.assertNotIn("receiver", repr(sample))
        self.assertTrue(all(type(value) is bool for value in sample.summary().values()))
        json.dumps(sample.summary())
        self.assertEqual(("_base", "_read"), state.__slots__)
        with self.assertRaises(FrozenInstanceError):
            sample.receiver = 7

    def test_relocation_uses_actual_module_base(self):
        relocated = BASE + 0x40000000
        memory = Memory(base=relocated)
        sample = native_state.NativeState(relocated, memory.read).sample()
        self.assertTrue(sample.playable)
        self.assertEqual(relocated + native_state.SINGLETON_RVA + 0x10, memory.calls[0][0])

    def test_state_is_compared_without_dereferencing_it(self):
        for state_pointer in (0, 1, 0xFFFFFFFFFFFFFFFF, BASE + native_state.APPVIEW_RVA + 8):
            with self.subTest(state_pointer=state_pointer):
                memory = Memory(state=state_pointer)
                sample = native_state.NativeState(BASE, memory.read).sample()
                self.assertFalse(sample.playable)
                self.assertNotIn(state_pointer, [address for address, _ in memory.calls])

    def test_every_pending_byte_participates_in_guard(self):
        for index in range(16):
            with self.subTest(index=index):
                pending = bytearray(16)
                pending[index] = 1
                memory = Memory(pending=pending)
                sample = native_state.NativeState(BASE, memory.read).sample()
                self.assertFalse(sample.pending_clear)

    def test_invalid_owner_is_never_dereferenced(self):
        for owner in (0, 8, OWNER + 1, OWNER + 8, 1 << 47, 0xFFFFFFFFFFFFFFF0,
                      (1 << 47) - native_state.OWNER_SIZE + 16):
            with self.subTest(owner=owner):
                memory = Memory(owner=owner)
                sample = native_state.NativeState(BASE, memory.read).sample()
                self.assertFalse(sample.owner_valid)
                self.assertEqual(0, sample.receiver)
                self.assertEqual(1, len(memory.calls))

    def test_partial_or_nonbytes_fixed_reads_fail_closed(self):
        for result in (None, b"", bytes(47), bytes(49), bytearray(48), "x" * 48):
            with self.subTest(type=type(result), length=len(result) if result is not None else 0):
                with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
                    native_state.NativeState(BASE, lambda _address, _size: result).sample()

    def test_unreadable_receiver_and_private_error_are_sanitized(self):
        memory = Memory()

        def read(address, size):
            if size == 16:
                raise RuntimeError("Secret pointer 0x1234")
            return memory.read(address, size)

        with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
            native_state.NativeState(BASE, read).sample()

    def test_partial_receiver_prefix_fails_closed(self):
        memory = Memory()
        with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
            native_state.NativeState(BASE, lambda a, s: b"x" if s == 16 else memory.read(a, s)).sample()

    def test_changes_during_read_fail_closed(self):
        for offset in (0, 8, 0x28):
            with self.subTest(offset=offset):
                memory = Memory()

                def read(address, size):
                    if size == 16:
                        memory.block[offset] ^= 1
                    return memory.read(address, size)

                with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
                    native_state.NativeState(BASE, read).sample()

    def test_later_callback_rereads_owner(self):
        memory = Memory()
        state = native_state.NativeState(BASE, memory.read)
        self.assertEqual(OWNER + native_state.CHAT_OFFSET, state.sample().receiver)
        struct.pack_into("<Q", memory.block, 0x28, OWNER + 0x1000000)
        memory.receiver += 0x1000000
        self.assertEqual(OWNER + 0x1000000 + native_state.CHAT_OFFSET, state.sample().receiver)

    def test_bad_module_bases_and_unmapped_fields_fail_before_read(self):
        for base in (0, 1, BASE + 1, True, "base", (1 << 47) - 0x10000):
            with self.subTest(base=base), self.assertRaises(ValueError):
                native_state.NativeState(base, lambda *_args: self.fail("Unexpected read"))
        with patch.object(native_state, "SINGLETON_RVA", native_state.IMAGE_SIZE - 8):
            with self.assertRaises(ValueError):
                native_state.NativeState(BASE, lambda *_args: self.fail("Unexpected read"))

    def test_non_windows_reader_is_refused(self):
        with patch.object(native_state.os, "name", "posix"):
            with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
                native_state.current_process_reader()

    @unittest.skipUnless(os.name == "nt", "Windows safe-reader check")
    def test_windows_reader_reads_only_its_own_original_buffer(self):
        import ctypes
        buffer = ctypes.create_string_buffer(b"original test data")
        read = native_state.current_process_reader()
        self.assertEqual(buffer.raw, read(ctypes.addressof(buffer), len(buffer.raw)))
        for address, size in ((0, 1), (ctypes.addressof(buffer), 0),
                              (ctypes.addressof(buffer), 4097), (1 << 47, 1)):
            with self.subTest(address_kind="invalid or bounded", size=size), self.assertRaises(ValueError):
                read(address, size)

    @unittest.skipUnless(os.name == "nt", "Windows safe-reader check")
    def test_windows_reader_refuses_failed_or_short_system_reads(self):
        import ctypes
        for success, count in ((False, 16), (True, 15)):
            with self.subTest(success=success, count=count):
                kernel = Mock()
                kernel.GetCurrentProcess.return_value = -1

                def system_read(_handle, _address, _buffer, _size, copied):
                    ctypes.cast(copied, ctypes.POINTER(ctypes.c_size_t))[0] = count
                    return success

                kernel.ReadProcessMemory.side_effect = system_read
                with patch.object(ctypes, "WinDLL", return_value=kernel):
                    read = native_state.current_process_reader()
                    with self.assertRaisesRegex(ValueError, "^Native memory read failed\\.$"):
                        read(OWNER, 16)


class LayoutTests(unittest.TestCase):
    def validate(self, data, spans, read_live=None, base=0, allow_fixture=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original-fixture.exe"
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest().upper() if allow_fixture else native_state.EXPECTED_SHA256
            with patch.object(native_state, "EXPECTED_SHA256", digest), patch.object(native_state, "GUARD_SPANS", spans):
                result = native_state.validate_layout(path, read_live, base)
            self.assertEqual(bytes(data), path.read_bytes())
            return result

    def test_file_and_live_reports_are_json_serializable(self):
        data, spans = synthetic_pe()
        report = self.validate(data, spans)
        self.assertTrue(report["eligible"])
        self.assertFalse(report["live_checked"])
        self.assertIsNone(report["spans"][0]["live_match"])
        json.dumps(report)
        calls = []

        def read(address, size):
            calls.append((address, size))
            offset = {BASE + 0x1000: 0x200, BASE + 0x2000: 0x400}[address]
            return bytes(data[offset:offset + size])

        report = self.validate(data, spans, read, BASE)
        self.assertTrue(report["live_checked"])
        self.assertTrue(all(row["live_match"] for row in report["spans"]))
        self.assertEqual([(BASE + 0x1000, 16), (BASE + 0x2000, 16)], calls)
        self.assertNotIn(str(BASE), json.dumps(report))

    def test_real_file_allowlist_refuses_synthetic_pe(self):
        data, spans = synthetic_pe()
        with self.assertRaisesRegex(ValueError, "^Native state layout refused\\.$"):
            self.validate(data, spans, allow_fixture=False)

    def test_file_span_tampering_refused_even_with_test_file_allowlist(self):
        data, spans = synthetic_pe()
        data[0x200] ^= 1
        with self.assertRaises(ValueError):
            self.validate(data, spans)

    def test_live_tampering_partial_and_private_errors_refused(self):
        data, spans = synthetic_pe()
        for output in (b"", bytes(16), bytes(17), None):
            with self.subTest(output_type=type(output)), self.assertRaisesRegex(ValueError, "^Native state layout refused\\.$"):
                self.validate(data, spans, lambda *_args: output, BASE)

        def read(*_args):
            raise RuntimeError("Secret native address")

        with self.assertRaisesRegex(ValueError, "^Native state layout refused\\.$"):
            self.validate(data, spans, read, BASE)

    def test_unmapped_fields_and_wrong_image_size_are_refused(self):
        for offset, value in ((0x188 + 2 * 40 + 8, 0x1000),
                              (0x98 + 56, native_state.IMAGE_SIZE + 0x1000)):
            data, spans = synthetic_pe()
            struct.pack_into("<I", data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.validate(data, spans)

    def test_truncated_file_bad_span_and_empty_profile_are_refused(self):
        data, spans = synthetic_pe()
        for size in (0, 63, 0x98, 0x1FF, 0x7FF):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.validate(data[:size], spans)
        for bad in ((), (native_state.GuardSpan("outside", 0x3000, 16, spans[0].sha256),),
                    (native_state.GuardSpan("empty", 0x1000, 0, spans[0].sha256),)):
            with self.subTest(profile=bad), self.assertRaises(ValueError):
                self.validate(data, bad)

    def test_live_validation_requires_real_base_before_reader(self):
        data, spans = synthetic_pe()
        with self.assertRaises(ValueError):
            self.validate(data, spans, lambda *_args: self.fail("Unexpected read"))

    def test_missing_file_error_is_fixed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "^Native state layout refused\\.$"):
                native_state.validate_layout(Path(directory) / "missing.exe")


if __name__ == "__main__":
    unittest.main()
