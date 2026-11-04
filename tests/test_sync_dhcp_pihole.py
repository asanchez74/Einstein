"""Tests de la synchronisation DHCP vers Pi-hole sur commandes id et docker simulées."""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/sync-synology-dhcp-to-pihole.sh"
LEASES = (
    "4102444800 aa:bb:cc:00:00:03 192.168.1.3 einstein *\n"
    "4102444800 aa:bb:cc:00:00:60 192.168.1.60 mac-mimi *\n"
    "1 aa:bb:cc:00:00:61 192.168.1.61 expire *\n"
)
EXPECTED = "192.168.1.3 einstein.chantevigne.com\n192.168.1.60 mac-mimi.chantevigne.com\n"


@pytest.fixture
def runtime(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    mounts = tmp_path / "mounts"
    for name in ("pihole", "pihole2"):
        (mounts / name).mkdir(parents=True)
    calls = tmp_path / "calls"
    calls.touch()
    leases = tmp_path / "leases"
    leases.write_text(LEASES)
    (binary / "id").write_text('#!/bin/sh\nprintf "%s\\n" "${FAKE_UID:-0}"\n')
    # timeout absent de macOS : même comportement via une alarme perl.
    (binary / "timeout").write_text(
        "#!/bin/sh\nexec perl -e 'alarm shift; exec @ARGV or exit 127' \"$@\"\n")
    # inspect : affiche le volume si mounts/<conteneur> existe ;
    # exec : journalise, échoue pour les conteneurs listés dans FAIL_EXEC,
    # reste bloqué pour ceux listés dans HANG_EXEC.
    (binary / "docker").write_text('''#!/bin/sh
case "$1" in
  inspect)
    eval "name=\\${$#}"
    [ -d "$MOUNTS_DIR/$name" ] || exit 1
    printf '%s\\n' "$MOUNTS_DIR/$name" ;;
  exec)
    echo "reload $2" >> "$CALLS_FILE"
    case " ${FAIL_EXEC:-} " in *" $2 "*) exit 1 ;; esac
    case " ${HANG_EXEC:-} " in *" $2 "*) exec sleep 30 ;; esac ;;
  *) exit 2 ;;
esac
''')
    for file in binary.iterdir():
        file.chmod(0o755)
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "LEASE_FILE": str(leases),
           "MOUNTS_DIR": str(mounts), "CALLS_FILE": str(calls)}

    def run(**overrides):
        return subprocess.run(["sh", str(SCRIPT)], env={**env, **overrides},
                              capture_output=True, text=True)
    return run, mounts, calls, leases


def hosts(mounts, name):
    return (mounts / name / "synology-hosts.list").read_text()


def test_both_targets_written_then_unchanged(runtime):
    run, mounts, calls, _ = runtime
    result = run()
    assert result.returncode == 0, result.stderr
    assert hosts(mounts, "pihole") == hosts(mounts, "pihole2") == EXPECTED
    assert calls.read_text() == "reload pihole\nreload pihole2\n"

    result = run()
    assert result.returncode == 0
    assert result.stdout.count("aucun changement (2 hôtes)") == 2
    assert calls.read_text() == "reload pihole\nreload pihole2\n"
    assert not list(mounts.rglob("*.tmp.*"))


def test_missing_target_does_not_block_other(runtime):
    run, mounts, calls, _ = runtime
    (mounts / "pihole2").rmdir()
    result = run()
    assert result.returncode == 1
    assert hosts(mounts, "pihole") == EXPECTED
    assert calls.read_text() == "reload pihole\n"
    assert "pihole2 : conteneur introuvable" in result.stderr
    assert "en échec pour : pihole2" in result.stderr


def test_reload_failure_reported_and_other_synced(runtime):
    run, mounts, calls, _ = runtime
    result = run(FAIL_EXEC="pihole")
    assert result.returncode == 1
    assert hosts(mounts, "pihole") == hosts(mounts, "pihole2") == EXPECTED
    assert calls.read_text() == "reload pihole\nreload pihole2\n"
    assert "en échec pour : pihole" in result.stderr


def test_hung_reload_times_out_and_other_synced(runtime):
    run, mounts, calls, _ = runtime
    result = run(HANG_EXEC="pihole", DOCKER_TIMEOUT="1")
    assert result.returncode == 1
    assert hosts(mounts, "pihole2") == EXPECTED
    assert calls.read_text() == "reload pihole\nreload pihole2\n"
    assert "délai de 1 s dépassé" in result.stderr
    assert "en échec pour : pihole" in result.stderr


def test_targets_are_configurable(runtime):
    run, mounts, calls, _ = runtime
    assert run(PIHOLE_TARGETS="pihole2").returncode == 0
    assert not (mounts / "pihole" / "synology-hosts.list").exists()
    assert calls.read_text() == "reload pihole2\n"


def test_no_usable_lease_keeps_files(runtime):
    run, mounts, calls, leases = runtime
    leases.write_text("1 aa:bb:cc:00:00:61 192.168.1.61 expire *\n")
    assert run().returncode == 1
    assert not list(mounts.rglob("synology-hosts.list"))
    assert not calls.read_text()


def test_non_root_refused(runtime):
    run, mounts, calls, _ = runtime
    assert run(FAKE_UID="501").returncode == 1
    assert not list(mounts.rglob("synology-hosts.list"))
