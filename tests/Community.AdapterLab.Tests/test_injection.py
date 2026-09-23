import ctypes
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "Community.AdapterLab"))
from injection import remote_module_base, write_to_mem


class ModuleAddressTests(unittest.TestCase):
    def test_uses_remote_base_and_exact_path(self):
        path = str(Path("local/runtime/python313.dll").resolve())
        modules = [SimpleNamespace(filename=path, lpBaseOfDll=0x230000000),
                   SimpleNamespace(filename=str(Path("other/python313.dll").resolve()),
                                   lpBaseOfDll=0x140000000)]
        self.assertEqual(remote_module_base(modules, path), 0x230000000)

    def test_missing_duplicate_and_null_module_refuse(self):
        path = str(Path("local/runtime/python313.dll").resolve())
        module = SimpleNamespace(filename=path, lpBaseOfDll=0x230000000)
        for modules in ([], [module, module], [SimpleNamespace(filename=path, lpBaseOfDll=0)]):
            with self.subTest(modules=modules), self.assertRaises(ValueError):
                remote_module_base(modules, path)


class PayloadWriteTests(unittest.TestCase):
    def setUp(self):
        self.copied = []

        def write(handle, address, buffer, count, written):
            self.copied.append(ctypes.string_at(buffer, count))
            ctypes.cast(written, ctypes.POINTER(ctypes.c_size_t)).contents.value = count
            return 1

        self.api = SimpleNamespace(
            VirtualAllocEx=Mock(return_value=0x230000000),
            WriteProcessMemory=Mock(side_effect=write),
            VirtualFreeEx=Mock(return_value=1),
        )

    def test_allocates_and_writes_exact_owned_bytes_with_terminator(self):
        for data, expected in ((b"original", b"original\0"),
                               (b"\x01\0\x02", b"\x01\0\x02\0"),
                               (b"", b"\0"),
                               ("\u00e9", b"\xc3\xa9\0")):
            with self.subTest(data=data):
                address = write_to_mem(self.api, 123, data)
                self.assertEqual(0x230000000, address)
                self.api.VirtualAllocEx.assert_called_with(123, None, len(expected), 0x3000, 0x04)
                self.assertEqual(expected, self.copied[-1])
                self.assertEqual(len(expected), self.api.WriteProcessMemory.call_args.args[3])
        self.api.VirtualFreeEx.assert_not_called()

    def test_failed_allocation_does_not_attempt_write_or_free(self):
        self.api.VirtualAllocEx.return_value = 0
        with self.assertRaisesRegex(OSError, "Cannot allocate"):
            write_to_mem(self.api, 123, b"original")
        self.api.WriteProcessMemory.assert_not_called()
        self.api.VirtualFreeEx.assert_not_called()

    def test_failed_or_partial_write_frees_allocation_and_refuses(self):
        for succeeded, count in ((0, 0), (0, 9), (1, 0), (1, 8)):
            with self.subTest(succeeded=succeeded, count=count):
                def write(handle, address, buffer, size, written):
                    ctypes.cast(written, ctypes.POINTER(ctypes.c_size_t)).contents.value = count
                    return succeeded

                self.api.WriteProcessMemory.side_effect = write
                self.api.VirtualFreeEx.reset_mock()
                with self.assertRaisesRegex(OSError, "not completely written"):
                    write_to_mem(self.api, 123, b"original")
                self.api.VirtualFreeEx.assert_called_once_with(123, 0x230000000, 0, 0x8000)

    def test_write_exception_also_frees_allocation(self):
        self.api.WriteProcessMemory.side_effect = OSError("Original failure")
        with self.assertRaisesRegex(OSError, "Original failure"):
            write_to_mem(self.api, 123, b"original")
        self.api.VirtualFreeEx.assert_called_once_with(123, 0x230000000, 0, 0x8000)

    def test_invalid_payload_does_not_allocate(self):
        with self.assertRaises(TypeError):
            write_to_mem(self.api, 123, 17)
        self.api.VirtualAllocEx.assert_not_called()
