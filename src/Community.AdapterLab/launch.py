"""Guarded lab attachment to an already-running disposable NMS session."""

import argparse
from importlib.metadata import distributions, entry_points
import json
from pathlib import Path
import socket
import sys

from runtime_guard import check_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--service-config", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13) or sys.prefix == sys.base_prefix:
        raise ValueError("Use the isolated CPython 3.13 lab venv")
    installed = {d.metadata["Name"].lower().replace("_", "-"): d.version
                 for d in distributions()}
    lock = json.loads((Path(__file__).parent / "dependencies.json").read_text(encoding="utf-8"))
    expected = {item["name"].lower().replace("_", "-"): item["version"] for item in lock}
    if {k: v for k, v in installed.items() if k != "pip"} != expected:
        raise ValueError("Lab dependencies differ from the reviewed dependency lock")
    if any(entry_points().select(group=group) for group in ("pymhflib", "pymhf_rtfunc")):
        raise ValueError("Unexpected pyMHF library/runtime plugin installed")
    # The upstream development REPL uses this port. Never attach to another session.
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 6770)) == 0:
            raise ValueError("pyMHF port 6770 is already occupied")
    report, _ = check_process(args.pid)
    run_dir = args.run_dir.resolve()
    allowed = Path(__file__).resolve().parents[2] / "local" / ("t04-3" if args.service_config else "t04-2")
    if not run_dir.is_relative_to(allowed) or run_dir == allowed:
        raise ValueError("Use a new run directory below the selected local task directory")
    service_config = None
    if args.service_config:
        from service_client import ClientConfig
        service_config = args.service_config.resolve()
        if not service_config.is_relative_to(allowed):
            raise ValueError("Use a private service config below local/t04-3")
        ClientConfig.load(service_config)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "preflight.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    import hashlib
    source_hashes = {source.name: hashlib.sha256(source.read_bytes()).hexdigest()
                     for source in Path(__file__).parent.glob("*.py")}
    (run_dir / "source-hashes.json").write_text(json.dumps(source_hashes, indent=2), encoding="utf-8")
    print("Preflight passed for candidate experiment; attaching to PID", args.pid, flush=True)
    # Explicit PID, no automatic launch/update, no GUI/HTTP extras/internal mods.
    # pyMHF constructs unused interactive prompts at import time. Supply a public
    # prompt_toolkit dummy session so redirected/headless runs need no console.
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import DummyInput
    from prompt_toolkit.output import DummyOutput
    with create_app_session(input=DummyInput(), output=DummyOutput()):
        import pymhf.main as injector
    from injection import checked_runner_type
    # Adapt only this launcher process; installed upstream files remain intact.
    injector.dllinject.pyRunner = checked_runner_type(injector.dllinject.pyRunner)
    config = {"pid": args.pid, "start_exe": False, "start_paused": False,
              "interactive_console": False, "cache_dir": str(run_dir / "cache"),
              "default_mod_save_dir": str(run_dir / "mod-saves"),
              "logging": {"log_dir": str(run_dir), "log_level": "info", "shown": False},
              "gui": {"shown": False}, "community_lab": {"run_dir": str(run_dir)}}
    if service_config:
        config["community_lab"]["service_config"] = str(service_config)
    injector.run_module(str(Path(__file__).with_name("probe.py")), config, config_dir=str(run_dir))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Adapter refused: {error}", file=sys.stderr)
        raise SystemExit(2)
