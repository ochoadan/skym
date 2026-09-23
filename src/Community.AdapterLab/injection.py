"""Narrow corrections for the selected upstream injector's address and buffer assumptions."""

import ctypes
from functools import partial
from pathlib import Path


def write_to_mem(api, handle, data):
    """Write an owned, terminated buffer; never read past a Python allocation.

    The pinned caller passes encoded strings and packed structs as bytes. An
    extra trailing zero is harmless for structs, whose readers use fixed sizes.
    The API argument permits source-only tests without opening a real process.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, bytes):
        raise TypeError("Injector payload must be bytes or text")
    payload = data + b"\0"
    buffer = ctypes.create_string_buffer(payload, len(payload))
    size = len(payload)
    # MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE.
    address = api.VirtualAllocEx(handle, None, size, 0x3000, 0x04)
    if not address:
        raise OSError("Cannot allocate injector payload in target process")
    try:
        written = ctypes.c_size_t()
        succeeded = api.WriteProcessMemory(handle, address, buffer, size, ctypes.byref(written))
        if not succeeded or written.value != size:
            raise OSError("Injector payload was not completely written to target process")
    except BaseException:
        api.VirtualFreeEx(handle, address, 0, 0x8000)  # MEM_RELEASE
        raise
    return address


def remote_module_base(modules, expected_path):
    expected = str(Path(expected_path).resolve()).casefold()
    matches = [module for module in modules
               if str(Path(module.filename).resolve()).casefold() == expected]
    if len(matches) != 1 or not matches[0].lpBaseOfDll:
        raise ValueError("The expected DLL was not uniquely loaded in the target process")
    return matches[0].lpBaseOfDll


def checked_runner_type(base_class):
    import sys
    import pyrun_injected.dll
    import pyrun_injected.dllinject as injector
    import pymem.ressources.kernel32 as memory_api
    from pyrun_injected.dllinject import StringType
    from pyrun_injected._win32utils import kernel32

    # The selected upstream write_string_data resolves this global at call time.
    # This changes only the current launcher interpreter, not installed files.
    injector.write_to_mem = partial(write_to_mem, memory_api)

    class CheckedRunner(base_class):
        def _inject_python_dll(self):
            super()._inject_python_dll()
            buffer = ctypes.create_unicode_buffer(32768)
            if not kernel32.GetModuleFileNameW(sys.dllhandle, buffer, len(buffer)):
                raise ValueError("Cannot locate the selected Python DLL")
            # Pymem 1.14 returns a local module handle after remote loading.
            # Resolve the actual target base before computing any remote address.
            self.python_lib_h = remote_module_base(self.pm.list_modules(), buffer.value)
            print("Verified Python DLL in target process", flush=True)

        def _inject_runpy_injected_dll(self):
            super()._inject_runpy_injected_dll()
            self.pyrun_lib_h = remote_module_base(
                self.pm.list_modules(), pyrun_injected.dll.__file__)
            import pefile
            import pymem.ressources.kernel32
            with pefile.PE(pyrun_injected.dll.__file__) as image:
                symbols = [item for item in image.DIRECTORY_ENTRY_EXPORT.symbols
                           if item.name == b"run_data" and not item.forwarder]
                if len(symbols) != 1 or not self.pyrun_handle:
                    raise ValueError("Injector export could not be uniquely resolved")
                rva = symbols[0].address
                if not any(section.Characteristics & 0x20000000 and
                           section.VirtualAddress <= rva < section.VirtualAddress + section.Misc_VirtualSize
                           for section in image.sections):
                    raise ValueError("Injector export is outside executable code")
                local_export = pymem.ressources.kernel32.GetProcAddress(self.pyrun_handle, b"run_data")
                if local_export != self.pyrun_handle + rva:
                    raise ValueError("Injector local export differs from the reviewed DLL")
                if self.pm.read_bytes(self.pyrun_lib_h + rva, 16) != image.get_data(rva, 16):
                    raise ValueError("Injector target export differs from its file")
            print("Verified injector export in target; relocated=" +
                  str(self.pyrun_lib_h != self.pyrun_handle), flush=True)

        def run_data(self, strings, **kwargs):
            # The pinned pyMHF prelude only imports pymhf.core._internal. Use the
            # public dummy session in the target too, before that first import.
            prelude = '''from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput
with create_app_session(input=DummyInput(), output=DummyOutput()):
    import pymhf.core._internal
'''
            rewritten = [StringType(prelude, False)
                         if item.is_file and Path(item.value).name == "_preinject.py"
                         else item for item in strings]
            return super().run_data(rewritten, **kwargs)

    return CheckedRunner
