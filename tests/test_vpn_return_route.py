"""Tests du script de routage sur commande ip simulée, sans toucher au réseau."""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/vpn-return-route.sh"
EXPECTED = "1: from 192.168.1.3 to 10.8.0.0/24 lookup main\n"


@pytest.fixture
def runtime(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    state = tmp_path / "rules"
    state.write_text("0: from all lookup local\n3: from 192.168.1.3 lookup ovs_bond0-table\n")
    calls = tmp_path / "calls"
    calls.touch()
    routes = tmp_path / "routes"
    routes.write_text("10.8.0.0/24 via 10.8.0.2 dev tun0\n")
    (binary / "id").write_text('#!/bin/sh\nprintf "%s\\n" "${FAKE_UID:-0}"\n')
    (binary / "ip").write_text('''#!/bin/sh
case "$*" in
  "-4 rule show") cat "$RULES_FILE" ;;
  "-4 route show table main") cat "$ROUTES_FILE" ;;
  "-4 rule add priority 1 from 192.168.1.3/32 to 10.8.0.0/24 lookup main")
    echo add >> "$CALLS_FILE"
    echo '1: from 192.168.1.3 to 10.8.0.0/24 lookup main' >> "$RULES_FILE" ;;
  "-4 rule del priority 1 from 192.168.1.3/32 to 10.8.0.0/24 lookup main")
    echo del >> "$CALLS_FILE"
    sed '/^1:/d' "$RULES_FILE" > "$RULES_FILE.new"
    mv "$RULES_FILE.new" "$RULES_FILE" ;;
  *) exit 2 ;;
esac
''')
    for file in binary.iterdir():
        file.chmod(0o755)
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "RULES_FILE": str(state),
           "ROUTES_FILE": str(routes), "CALLS_FILE": str(calls)}

    def run(action, **overrides):
        return subprocess.run(["sh", str(SCRIPT), action], env={**env, **overrides},
                              capture_output=True, text=True)
    return run, state, calls, routes


def test_apply_check_remove_idempotent(runtime):
    run, state, calls, _ = runtime
    assert run("--check").returncode == 1
    assert run("--apply").returncode == 0
    assert run("--apply").returncode == 0
    assert run("--check").returncode == 0
    assert calls.read_text() == "add\n"
    assert run("--remove").returncode == 0
    assert run("--remove").returncode == 0
    assert calls.read_text() == "add\ndel\n"
    assert "3: from 192.168.1.3 lookup ovs_bond0-table" in state.read_text()


@pytest.mark.parametrize("action", ["--apply", "--remove"])
def test_conflict_is_never_overwritten(runtime, action):
    run, state, calls, _ = runtime
    state.write_text(state.read_text() + "1: from all lookup other\n")
    assert run(action).returncode == 1
    assert not calls.read_text()


def test_duplicate_priority_refused(runtime):
    run, state, calls, _ = runtime
    state.write_text(EXPECTED + EXPECTED)
    assert run("--apply").returncode == 1
    assert not calls.read_text()


def test_tunnel_not_ready_defers_mutation(runtime):
    run, _, calls, routes = runtime
    routes.write_text("default via 192.168.1.1 dev ovs_bond0\n")
    assert run("--apply").returncode == 0
    assert not calls.read_text()


def test_non_root_cannot_modify(runtime):
    run, _, calls, _ = runtime
    assert run("--apply", FAKE_UID="1000").returncode == 1
    assert not calls.read_text()
