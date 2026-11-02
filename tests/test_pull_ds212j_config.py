"""Tests de la copie de configuration DS212j sur commande rsync simulée."""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/pull-ds212j-config.sh"


@pytest.fixture
def runtime(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    args_file = tmp_path / "rsync-args"
    key = tmp_path / "key"
    key.write_text("cle")
    dest = tmp_path / "dest"
    # Enregistre un argument par ligne ; échoue si RSYNC_FAIL est défini.
    (binary / "rsync").write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGS_FILE"\n[ -z "${RSYNC_FAIL:-}" ]\n'
    )
    (binary / "rsync").chmod(0o755)
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
           "ARGS_FILE": str(args_file), "SSH_KEY": str(key), "DEST_DIR": str(dest)}

    def run(**overrides):
        return subprocess.run(["sh", str(SCRIPT)], env={**env, **overrides},
                              capture_output=True, text=True)
    return run, args_file, dest


def test_copies_sources_without_deleting(runtime):
    run, args_file, dest = runtime
    result = run()
    assert result.returncode == 0, result.stderr
    args = args_file.read_text().splitlines()
    assert "--relative" in args
    assert not any(arg.startswith("--delete") for arg in args)
    assert "tonio@192.168.1.4:/volume1/web/maison" in args
    assert "tonio@192.168.1.4:/volume1/@optware" in args
    assert "tonio@192.168.1.4:/opt/etc/init.d/S98eibd" in args
    assert args[-1] == f"{dest}/"
    assert any("-p 22606" in arg and "BatchMode=yes" in arg for arg in args)
    assert dest.is_dir()


def test_rsync_failure_is_reported(runtime):
    run, _, dest = runtime
    result = run(RSYNC_FAIL="1")
    assert result.returncode == 1
    assert f"en échec vers {dest}" in result.stderr


def test_missing_key_refused(runtime, tmp_path):
    run, args_file, _ = runtime
    result = run(SSH_KEY=str(tmp_path / "absente"))
    assert result.returncode == 1
    assert "clé SSH illisible" in result.stderr
    assert not args_file.exists()
