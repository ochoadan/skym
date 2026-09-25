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
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument("--observe-world", action="store_true",
                        help="T-04.5 observation only; cannot connect a service")
    profiles.add_argument("--validate-world", action="store_true",
                          help="T-04.5 read-only receiver/state validation; no service")
    profiles.add_argument("--auto-world", action="store_true",
                          help="T-04.5 attended cockpit and automatic presentation experiment")
    parser.add_argument("--delivery-delay", type=float, default=0.0,
                        help="Automatic profile only: presentation delay in seconds, 0..10")
    args = parser.parse_args()
    if (args.observe_world or args.validate_world) and args.service_config:
        raise ValueError("World observation cannot connect a service")
    if args.auto_world and not args.service_config:
        raise ValueError("Automatic world mode requires a service configuration")
    if not 0 <= args.delivery_delay <= 10 or (args.delivery_delay and not args.auto_world):
        raise ValueError("Delivery delay requires automatic world mode and a value from 0 to 10")
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
    report, _ = check_process(args.pid, observe_world=args.observe_world,
                             validate_world=args.validate_world or args.auto_world)
    run_dir = args.run_dir.resolve()
    local = Path(__file__).resolve().parents[2] / "local"
    tasks = (("t04-5",) if args.observe_world or args.validate_world or args.auto_world else
             ("t04-3", "t04-4") if args.service_config else ("t04-2",))
    allowed = next((local / task for task in tasks
                    if run_dir.is_relative_to(local / task) and run_dir != local / task), None)
    if allowed is None:
        raise ValueError("Use a new run directory below the selected local task directory")
    service_config = None
    if args.service_config:
        from service_client import ClientConfig
        service_config = args.service_config.resolve()
        if not service_config.is_relative_to(allowed):
            raise ValueError("Use a private service config below the same local task directory as the run")
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
    config["community_lab"]["observe_world"] = args.observe_world
    config["community_lab"]["validate_world"] = args.validate_world
    config["community_lab"]["auto_world"] = args.auto_world
    config["community_lab"]["delivery_delay"] = args.delivery_delay
    if service_config:
        config["community_lab"]["service_config"] = str(service_config)
    injector.run_module(str(Path(__file__).with_name("probe.py")), config, config_dir=str(run_dir))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Adapter refused: {error}", file=sys.stderr)
        raise SystemExit(2)
