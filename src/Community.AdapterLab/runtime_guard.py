"""Read-only checks of the actual process before installing the two lab hooks."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from preflight import inspect_executable, SIGNATURES


def check_process(pid: int):
    # These imports do not install hooks or inject Python.
    import psutil
    import pymem
    import pymem.pattern
    import pymem.process

    process = psutil.Process(pid)
    path = Path(process.exe())
    if path.name.lower() != "nms.exe":
        raise ValueError("The selected process is not NMS.exe")
    settings = ET.parse(path.parent / "SETTINGS" / "GCUSERSETTINGSDATA.MXML")
    for key in ("Multiplayer", "CrossSaves"):
        values = [node.get("value") for node in settings.iter("Property") if node.get("name") == key]
        if values != ["false"]:
            raise ValueError(f"The lab requires {key}=false in the recorded game settings")
    report = inspect_executable(path)
    if not report["eligible"]:
        raise ValueError(f"Executable preflight refused: {report}")
    memory = pymem.Pymem(pid)
    try:
        module = pymem.process.module_from_name(memory.process_handle, path.name)
        if module is None:
            raise ValueError("NMS executable module is absent")
        rvas = {}
        for name, signature in SIGNATURES.items():
            pattern = b"".join(b"." if s in ("?", "??") else
                               re.escape(bytes.fromhex(s)) for s in signature.split())
            matches = pymem.pattern.pattern_scan_module(
                memory.process_handle, module, pattern, return_multiple=True)
            actual = [address - module.lpBaseOfDll for address in (matches or [])]
            expected = report["signatures"][name]["rvas"]
            if actual != expected or len(actual) != 1:
                raise ValueError(f"Live signature refused: {name}; count={len(actual)}")
            rvas[name] = actual[0]
        return report, rvas
    finally:
        memory.close_process()
