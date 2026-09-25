"""Exact-build, read-only receiver/state candidate for the attended T-04.5 lab.

Offsets and span hashes record local static findings; they are not a stable API.
Successful reads do not prove lifetime, focus, pause state, or safe native calls.
Never retain a Sample beyond the engine callback that requested it.
"""

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import struct

from preflight import _file_offset, _parse_pe


EXPECTED_SHA256 = "B7913F268DFC62386B6B68F524BFC8ADE4A44A9F4FBAD39085B7BF51BE3680CB"
IMAGE_SIZE = 0x760A000
SINGLETON_RVA = 0x6E7AAB0
APPVIEW_RVA = 0x6E7C520
CHAT_OFFSET = 0x932AB0
OWNER_SIZE = 0x94F120
_USER_LIMIT = 1 << 47
_MAX_READ = 4096
_READ_ERROR = "Native memory read failed."
_LAYOUT_ERROR = "Native state layout refused."


@dataclass(frozen=True)
class GuardSpan:
    name: str
    rva: int
    length: int
    sha256: str


# Whole instruction spans avoid detour entry prefixes. None contains a PE base
# relocation. Only hashes/locations are recorded here, never executable bytes.
# The state table is in a writable section: live equality is required, rather
# than an assumption that section permissions make the table immutable.
GUARD_SPANS = (
    GuardSpan("chat_receiver", 0xB14284, 22,
              "6F0264DCFDD9170BFACFAE588AF62FA85B732C37F4D20F958A00F1E7FAB49E8E"),
    GuardSpan("system_receiver", 0xB151A3, 19,
              "CABBF52C9CD188870EE4D224824744EC9871963145335A90C2207B5091D6343A"),
    GuardSpan("owner_init_and_state_table", 0x2C6BEB, 95,
              "519F5836F61DE331A45DA8575DA8E1A276654C13917BD37CC82669D270E68300"),
    GuardSpan("owner_zero", 0x32BB06, 24,
              "56E6BB02836DD8A110A826B22EA37352C59739F6AADF83E3130332B8FBEBD53A"),
    GuardSpan("owner_clear", 0x627D19, 44,
              "FE0D00F417F03587641D3B3546BE90B802DA79D01C97D5D8C1BACACDC41DB7E0"),
    GuardSpan("app_fsm_update", 0x2D76E8, 20,
              "C43E3B7BFE011358A369011C4507C0EBABC32A95976D5CDA30FBBE2EA10F405C"),
    GuardSpan("current_state_store", 0x2BD92F2, 20,
              "14031D38F395DA2843178C1F5AC2D2CDDB7F59E05E65F12886A7E7AB66DF7D63"),
    GuardSpan("pending_queue", 0x2BD8320, 48,
              "E95EF153E88944D85092D706D3E770702681E5A4CA60770E982CE36D39A3AC33"),
    GuardSpan("pending_update", 0x2BD96B0, 88,
              "AFFD17EAD742695E3D270866670EB9115798687D9E11249AC6202CC30A60AECD"),
    GuardSpan("fsm_construct", 0x2BD47E4, 103,
              "1CF894D1E3FFD277088E11762A103DDEDD7859910307FE0231EBAED300CDAA63"),
    GuardSpan("empty_pending", 0x350AB80, 16,
              "374708FFF7719DD5979EC875D56CD2286F6D3CF7EC317A3B25632AAB28EC37BB"),
    GuardSpan("state_table", 0x507FF00, 336,
              "A904A51E085ECD109D9E829C673F599A8B99301013186418090DB2E6E5EB164B"),
)


def _address_ok(address, size):
    return (type(address) is int and type(size) is int and size > 0
            and 0x10000 <= address < _USER_LIMIT and size <= _USER_LIMIT - address)


def _module_address(base, rva, size):
    if (not _address_ok(base, IMAGE_SIZE) or base % 0x10000
            or type(rva) is not int or type(size) is not int
            or rva < 0 or size <= 0 or rva > IMAGE_SIZE - size):
        raise ValueError(_READ_ERROR)
    return base + rva


def _read_exact(read, address, size):
    if not _address_ok(address, size) or size > _MAX_READ:
        raise ValueError(_READ_ERROR)
    try:
        result = read(address, size)
        if not isinstance(result, bytes) or len(result) != size:
            raise ValueError(_READ_ERROR)
        return result
    except Exception:
        # Reader errors may contain native addresses; never pass them to logs.
        raise ValueError(_READ_ERROR) from None


def validate_layout(path, read_live=None, base=0):
    """Verify the allowed file and guarded spans; optionally verify mapped bytes.

    No game process is opened. The caller supplies an exact-size safe reader and
    the actual loaded module base when checking live memory. The report contains
    RVAs/hashes only, and is safe to serialize as JSON.
    """
    try:
        data = Path(path).read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if digest != EXPECTED_SHA256:
            raise ValueError(_LAYOUT_ERROR)
        sections, _, _ = _parse_pe(data, {})
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if struct.unpack_from("<I", data, pe_offset + 24 + 56)[0] != IMAGE_SIZE:
            raise ValueError(_LAYOUT_ERROR)
        # Mutable state fields can be zero-filled image data, so check mapped
        # sections rather than requiring an initialized file range.
        for rva, length in ((SINGLETON_RVA, 0x40), (APPVIEW_RVA, 0x10)):
            if not any(s.rva <= rva and rva + length <= s.rva + s.size for s in sections):
                raise ValueError(_LAYOUT_ERROR)
        if not GUARD_SPANS:
            raise ValueError(_LAYOUT_ERROR)
        checks = []
        for span in GUARD_SPANS:
            if span.length <= 0 or span.length > _MAX_READ:
                raise ValueError(_LAYOUT_ERROR)
            offset = _file_offset(sections, span.rva, span.length)
            if hashlib.sha256(data[offset:offset + span.length]).hexdigest().upper() != span.sha256:
                raise ValueError(_LAYOUT_ERROR)
            if read_live is not None:
                address = _module_address(base, span.rva, span.length)
                live = _read_exact(read_live, address, span.length)
                if hashlib.sha256(live).hexdigest().upper() != span.sha256:
                    raise ValueError(_LAYOUT_ERROR)
            checks.append({"name": span.name, "rva": span.rva, "length": span.length,
                           "sha256": span.sha256, "file_match": True,
                           "live_match": True if read_live is not None else None})
        return {"profile": "t04-5-native-state", "sha256": digest,
                "image_size": IMAGE_SIZE, "eligible": True,
                "live_checked": read_live is not None, "spans": checks}
    except (OSError, ValueError, TypeError, struct.error):
        raise ValueError(_LAYOUT_ERROR) from None


@dataclass(frozen=True)
class Sample:
    # Omitting the pointer from repr reduces accidental diagnostic disclosure.
    receiver: int = field(repr=False)
    playable: bool
    pending_clear: bool
    owner_valid: bool

    def summary(self):
        return {"playable": self.playable, "pending_clear": self.pending_clear,
                "owner_valid": self.owner_valid}


class NativeState:
    """Fresh callback-local reads; the accessor never caches a native pointer."""

    __slots__ = ("_base", "_read")

    def __init__(self, base, read):
        _module_address(base, SINGLETON_RVA, 0x40)
        _module_address(base, APPVIEW_RVA, 0x10)
        if not callable(read):
            raise ValueError(_READ_ERROR)
        self._base = base
        self._read = read

    def sample(self):
        address = _module_address(self._base, SINGLETON_RVA + 0x10, 0x30)
        block = _read_exact(self._read, address, 0x30)
        state = struct.unpack_from("<Q", block)[0]
        owner = struct.unpack_from("<Q", block, 0x28)[0]
        playable = state == _module_address(self._base, APPVIEW_RVA, 0x10)
        pending_clear = not any(block[8:24])
        owner_valid = _address_ok(owner, OWNER_SIZE) and owner % 16 == 0
        if not owner_valid:
            return Sample(0, playable, pending_clear, False)
        receiver = owner + CHAT_OFFSET
        # Only check readability; do not interpret this object or follow any of
        # its pointer fields. This does not certify the whole allocation.
        _read_exact(self._read, receiver, 16)
        if _read_exact(self._read, address, 0x30) != block:
            raise ValueError(_READ_ERROR)
        return Sample(receiver, playable, pending_clear, True)


def current_process_reader():
    """Return a bounded safe reader for this Windows process only."""
    if os.name != "nt":
        raise ValueError(_READ_ERROR)
    import ctypes
    from ctypes import wintypes

    if ctypes.sizeof(ctypes.c_void_p) != 8:
        raise ValueError(_READ_ERROR)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_process = kernel.GetCurrentProcess
    get_process.argtypes = []
    get_process.restype = wintypes.HANDLE
    read_memory = kernel.ReadProcessMemory
    read_memory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                           ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    read_memory.restype = wintypes.BOOL
    handle = get_process()  # Pseudo-handle: must not be closed.

    def read(address, size):
        if not _address_ok(address, size) or size > _MAX_READ:
            raise ValueError(_READ_ERROR)
        buffer = ctypes.create_string_buffer(size)
        copied = ctypes.c_size_t()
        if (not read_memory(handle, ctypes.c_void_p(address), buffer, size, ctypes.byref(copied))
                or copied.value != size):
            raise ValueError(_READ_ERROR)
        return buffer.raw

    return read
