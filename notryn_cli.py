#!/usr/bin/env python3
"""Lifecycle command for the local Notryn application."""

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from notryn_version import VERSION
from notryn_install import Installation
from server import serve

DEFAULT_PORT = 4783
APP_ID = "notryn"


def data_home(platform=None, environ=None, home=None):
    platform = platform or sys.platform
    environ = os.environ if environ is None else environ
    configured = environ.get("NOTRYN_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    home = Path(home or Path.home()).expanduser().resolve()
    if platform == "darwin":
        return home / "Library" / "Application Support" / "Notryn"
    if platform == "win32":
        return Path(environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "Notryn"
    return Path(environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "notryn"


def runtime_path(home):
    return Path(home) / "runtime.json"


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".notryn-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_runtime(home):
    try:
        value = json.loads(runtime_path(home).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return None
        if not isinstance(value.get("port"), int) or not isinstance(value.get("instance"), str):
            return None
        return value
    except (OSError, ValueError):
        return None


def probe(record, timeout=0.5):
    if not record:
        return None
    try:
        with urlopen(f"http://127.0.0.1:{record['port']}/api/runtime", timeout=timeout) as response:
            value = json.loads(response.read())
        if value.get("app") == APP_ID and secrets.compare_digest(value.get("instance", ""), record["instance"]):
            return value
    except (OSError, URLError, ValueError, KeyError):
        pass
    return None


def process_command(command, home, port, instance):
    arguments = ["serve", "--data-dir", str(home), "--port", str(port), "--instance=" + instance]
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    return [sys.executable, str(Path(__file__).resolve()), *arguments]


def start(home, port=DEFAULT_PORT):
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = home / 'installation.lock'
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise RuntimeError('An installation or startup is in progress. Open Notryn when it finishes.')
    try:
        return start_locked(home, port)
    finally:
        lock.rmdir()


def start_locked(home, port):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(home, 0o700)
    except OSError:
        pass
    current = read_runtime(home)
    live = probe(current)
    if live:
        return current, False
    runtime_path(home).unlink(missing_ok=True)
    instance = secrets.token_urlsafe(24)
    logs = home / "logs"
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_path = logs / "server.log"
    record = {
        "app": APP_ID,
        "version": VERSION,
        "pid": None,
        "port": port,
        "instance": instance,
        "startedAt": datetime.now(timezone.utc).isoformat(),
    }
    environment = os.environ.copy()
    environment["NOTRYN_HOME"] = str(home)
    with log_path.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            process_command("serve", home, port, instance),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
            env=environment,
        )
    record["pid"] = process.pid
    atomic_json(runtime_path(home), record)
    for _ in range(50):
        if probe(record, timeout=0.2):
            return record, True
        if process.poll() is not None:
            break
        time.sleep(0.1)
    runtime_path(home).unlink(missing_ok=True)
    detail = ""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
    try:
        detail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-1]
    except (OSError, IndexError):
        pass
    raise RuntimeError("Notryn could not start." + (" " + detail if detail else ""))


def open_url(port):
    url = f"http://127.0.0.1:{port}/"
    if sys.platform == "darwin" and Path("/usr/bin/open").exists():
        subprocess.Popen(["/usr/bin/open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def stop(home):
    home = Path(home)
    record = read_runtime(home)
    if not probe(record):
        runtime_path(home).unlink(missing_ok=True)
        return False
    try:
        os.kill(record["pid"], signal.SIGTERM)
    except (OSError, TypeError):
        return False
    for _ in range(50):
        if not probe(record, timeout=0.1):
            runtime_path(home).unlink(missing_ok=True)
            return True
        time.sleep(0.1)
    return False


def copy_state(source, destination):
    source_input = Path(source).expanduser().absolute()
    source = source_input.resolve()
    destination = Path(destination).expanduser().resolve()
    if not source.is_dir() or not (source / "brains.json").is_file():
        raise RuntimeError("The source is not a Notryn or legacy Neura state directory.")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise RuntimeError("State migration refuses symbolic links.")
    if (destination / "brains.json").exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = destination.parent / ("." + destination.name + ".migrate-" + secrets.token_hex(6))
    try:
        shutil.copytree(source, temporary)
        old_paths = {str(source_input), str(source)}
        new = str(destination)
        for path in temporary.rglob("*.json"):
            content = path.read_text(encoding="utf-8")
            updated = content
            for old in old_paths:
                updated = updated.replace(old, new)
            json.loads(updated)
            path.write_text(updated, encoding="utf-8")
        if destination.exists():
            if any(destination.iterdir()):
                raise RuntimeError("The destination state directory is not empty.")
            destination.rmdir()
        os.replace(temporary, destination)
        try:
            os.chmod(destination, 0o700)
        except OSError:
            pass
        return True
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def parser():
    result = argparse.ArgumentParser(prog="notryn", description="Start and manage the local Notryn app.")
    result.add_argument("command", nargs="?", default="open", choices=["open", "start", "stop", "status", "version", "serve", "migrate-state", "update", "rollback", "uninstall"])
    result.add_argument('--version', dest='release_version', nargs='?', const='current', help='Show version, or select a release for update')
    result.add_argument("--port", type=int, default=DEFAULT_PORT)
    result.add_argument("--data-dir")
    result.add_argument("--instance")
    result.add_argument("--source")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.release_version == 'current':
        print(VERSION)
        return 0
    home = Path(args.data_dir).expanduser().resolve() if args.data_dir else data_home()
    try:
        if args.command == "serve":
            if not args.instance:
                raise RuntimeError("Missing private runtime identity.")
            return serve(port=args.port, data_dir=home, instance_id=args.instance)
        if args.command == "version":
            print(VERSION)
            return 0
        if args.command == "migrate-state":
            if not args.source:
                raise RuntimeError("Pass --source with the previous private state directory.")
            changed = copy_state(args.source, home)
            print("State migrated to " + str(home) + "." if changed else "Existing Notryn state was kept.")
            return 0
        if args.command == "status":
            record = read_runtime(home)
            if probe(record):
                print(f"Notryn is running at http://127.0.0.1:{record['port']}/ (PID {record['pid']}).")
                return 0
            print("Notryn is stopped.")
            return 1
        if args.command == "stop":
            print("Notryn stopped." if stop(home) else "Notryn was already stopped.")
            return 0
        if args.command == "uninstall":
            Installation(data=home).uninstall()
            return 0
        if args.command == "update":
            Installation(data=home).update(args.release_version)
            return 0
        if args.command == "rollback":
            Installation(data=home).rollback()
            return 0
        if args.command == 'open' and getattr(sys, 'frozen', False):
            Installation(data=home).open()
            return 0
        record, created = start(home, args.port)
        if args.command == "open":
            open_url(record["port"])
        print(("Notryn started" if created else "Notryn is already running") + f" at http://127.0.0.1:{record['port']}/.")
        return 0
    except KeyboardInterrupt:
        print('\nOperation cancelled.', file=sys.stderr)
        return 130
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
