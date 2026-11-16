"""Tests de la copie vers le disque externe, avec df, date, open et rsync simulés."""

import os
from pathlib import Path
import subprocess
import time

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/mac-usb-backup.sh"


@pytest.fixture
def runtime(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    source = tmp_path / "source"
    hbk = source / "DS918.hbk"
    (hbk / "Pool").mkdir(parents=True)
    (hbk / "_Syno_TaskConfig").write_text("data_encrypt=true\n")
    (source / "lisbonne2027").mkdir()
    old = time.time() - 3 * 3600
    for path in [hbk / "Pool", hbk / "_Syno_TaskConfig", hbk, source / "lisbonne2027"]:
        os.utime(path, (old, old))
    dest = tmp_path / "usb"
    dest.mkdir()
    calls = tmp_path / "calls"
    calls.touch()

    # df : le point de montage annoncé est FAKE_MOUNT (par défaut la destination).
    (binary / "df").write_text(
        '#!/bin/sh\necho "Filesystem 512-blocks Used Available Capacity Mounted on"\n'
        'echo "/dev/disk6 100 10 90 10% ${FAKE_MOUNT}"\n')
    (binary / "date").write_text(
        '#!/bin/sh\ncase "$1" in +%H) echo "${FAKE_HOUR:-14}" ;; +%s) /bin/date +%s ;; *) echo "2026-11-14 14:00:00" ;; esac\n')
    (binary / "open").write_text('#!/bin/sh\necho "open $*" >> "$CALLS_FILE"\n')
    (binary / "rsync").write_text(
        '#!/bin/sh\necho "rsync $*" >> "$CALLS_FILE"\n'
        '[ -z "${TOUCH_DURING_COPY:-}" ] || touch "$TOUCH_DURING_COPY"\n'
        'exit "${RSYNC_EXIT:-0}"\n')
    (binary / "sleep").write_text('#!/bin/sh\nexit 0\n')
    for file in binary.iterdir():
        file.chmod(0o755)

    env = {**os.environ, "PATH": f"{binary}:/usr/bin:/bin", "SOURCE_ROOT": str(source),
           "DEST_ROOT": str(dest), "FAKE_MOUNT": str(dest), "CALLS_FILE": str(calls),
           "MOUNT_WAIT": "2"}

    def run(*args, **overrides):
        return subprocess.run(["sh", str(SCRIPT), *args], env={**env, **overrides},
                              capture_output=True, text=True)
    return run, source, dest, calls


def test_mirrors_each_item_into_its_own_directory(runtime):
    run, source, dest, calls = runtime
    result = run()
    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == [
        f"rsync -rlt --delete {source}/DS918.hbk/ {dest}/DS212j/DS918.hbk/",
        f"rsync -rlt --delete {source}/lisbonne2027/ {dest}/DS212j/lisbonne2027/",
    ]
    assert "Debut=2026-11-14 14:00:00" in (dest / "DS212j/DERNIERE-COPIE.txt").read_text()


def test_dry_run_passes_flag_and_writes_no_marker(runtime):
    run, _, dest, calls = runtime
    result = run("--dry-run")
    assert result.returncode == 0, result.stderr
    assert all("--dry-run" in line for line in calls.read_text().splitlines())
    assert not (dest / "DS212j/DERNIERE-COPIE.txt").exists()
    assert "simulation" in result.stdout


def test_refuses_destination_that_is_not_a_mount_point(runtime):
    run, _, _, calls = runtime
    result = run(FAKE_MOUNT="/")
    assert result.returncode == 1
    assert "n'est pas un volume monté" in result.stderr
    assert not calls.read_text()


def test_refuses_missing_disk(runtime, tmp_path):
    run, _, _, calls = runtime
    result = run(DEST_ROOT=str(tmp_path / "absent"))
    assert result.returncode == 1
    assert "disque externe absent" in result.stderr
    assert not calls.read_text()


def test_refuses_during_nightly_backup_hour(runtime):
    run, _, _, calls = runtime
    result = run(FAKE_HOUR="04")
    assert result.returncode == 1
    assert "sauvegarde nocturne" in result.stderr
    assert "rsync" not in calls.read_text()


def test_refuses_recently_modified_repository(runtime):
    run, source, _, calls = runtime
    (source / "DS918.hbk/Pool").touch()
    result = run()
    assert result.returncode == 1
    assert "modifié depuis moins de 30 min" in result.stderr
    assert "rsync" not in calls.read_text()


def test_mounts_source_when_absent_then_fails_cleanly(runtime, tmp_path):
    run, _, _, calls = runtime
    result = run(SOURCE_ROOT=str(tmp_path / "pas-monte"))
    assert result.returncode == 1
    assert "dépôt Hyper Backup introuvable" in result.stderr
    assert calls.read_text().startswith("open smb://tonio@192.168.1.4/SauvegardeDS918")


def test_rejects_unknown_option(runtime):
    run, _, _, _ = runtime
    assert run("--delete-all").returncode == 2


def test_fails_when_repository_changes_during_copy(runtime):
    run, source, dest, _ = runtime
    result = run(TOUCH_DURING_COPY=str(source / "DS918.hbk/Pool"))
    assert result.returncode == 1
    assert "modifié pendant la copie" in result.stderr
    assert not (dest / "DS212j/DERNIERE-COPIE.txt").exists()


def test_fails_when_rsync_fails(runtime):
    run, _, dest, calls = runtime
    result = run(RSYNC_EXIT="23")
    assert result.returncode == 1
    assert "code 23" in result.stderr
    assert len(calls.read_text().splitlines()) == 2
    assert not (dest / "DS212j/DERNIERE-COPIE.txt").exists()
