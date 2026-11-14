"""Tests de la surveillance de saturation sur fichiers /proc et docker simulés."""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/nas-health-check.sh"

MEMINFO = """MemTotal:        7989260 kB
MemFree:          400000 kB
MemAvailable:    {available} kB
SwapTotal:       6893484 kB
SwapFree:        {swap_free} kB
"""

MDSTAT_OK = """Personalities : [raid1] [raid6] [raid5] [raid4]
md2 : active raid5 sda5[0] sdd5[3] sdc5[2] sdb5[1]
      11706562368 blocks super 1.2 level 5, 64k chunk, algorithm 2 [4/4] [UUUU]

md3 : active raid1 nvme0n1p1[0] nvme1n1p1[1]
      488381952 blocks super 1.2 [2/2] [UU]

md1 : active raid1 sda2[0] sdc2[3] sdd2[2] sdb2[1]
      2097088 blocks [4/4] [UUUU]

unused devices: <none>
"""


def cpu_line(total_idle, iowait):
    # user nice system idle iowait irq softirq steal guest guest_nice
    return f"cpu  1000 0 1000 {total_idle} {iowait} 0 0 0 0 0\nprocs_blocked 0\n"


@pytest.fixture
def runtime(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    proc = {
        "stat": tmp_path / "stat",
        "stat_after": tmp_path / "stat_after",
        "meminfo": tmp_path / "meminfo",
        "mdstat": tmp_path / "mdstat",
        "loadavg": tmp_path / "loadavg",
    }
    proc["stat"].write_text(cpu_line(10000, 100))
    proc["stat_after"].write_text(cpu_line(10900, 200))  # 100/1000 = 10 %
    proc["meminfo"].write_text(MEMINFO.format(available=5427276, swap_free=6260180))
    proc["mdstat"].write_text(MDSTAT_OK)
    proc["loadavg"].write_text("0.70 0.54 0.52 1/1013 20835\n")
    state = tmp_path / "state"

    (binary / "id").write_text('#!/bin/sh\nprintf "%s\\n" "${FAKE_UID:-0}"\n')
    # L'échantillon : « sleep » remplace /proc/stat par sa valeur suivante.
    (binary / "sleep").write_text('#!/bin/sh\ncp "$STAT_AFTER" "$PROC_STAT"\n')
    (binary / "timeout").write_text('#!/bin/sh\nshift\nexec "$@"\n')
    (binary / "docker").write_text('''#!/bin/sh
case "$1" in
  inspect)
    [ "$FAKE_RUNNING" = absent ] && exit 1
    [ "$FAKE_RUNNING" = hang ] && exit 124
    echo "$FAKE_RUNNING" ;;
  exec) exit "${FAKE_EXEC_RC:-0}" ;;
  version) exit "${FAKE_VERSION_RC:-0}" ;;
  *) exit 2 ;;
esac
''')
    for file in binary.iterdir():
        file.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{binary}:/usr/bin:/bin",
        "PROC_STAT": str(proc["stat"]),
        "STAT_AFTER": str(proc["stat_after"]),
        "PROC_MEMINFO": str(proc["meminfo"]),
        "PROC_MDSTAT": str(proc["mdstat"]),
        "PROC_LOADAVG": str(proc["loadavg"]),
        "STATE_FILE": str(state),
        "FAKE_RUNNING": "true",
    }

    def run(**overrides):
        # Chaque exécution repart du premier relevé de /proc/stat.
        proc["stat"].write_text(cpu_line(10000, 100))
        return subprocess.run(["sh", str(SCRIPT)], env={**env, **overrides},
                              capture_output=True, text=True)

    return run, proc, state


def test_healthy_system_reports_one_line(runtime):
    run, _, state = runtime
    result = run()
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("charge 0.70 0.54 0.52 ; attente disque 10 %")
    assert "swap 618 Mo" in result.stdout
    assert "RAID ok ; docker ok" in result.stdout
    assert state.read_text() == "iowait_high_runs=0\n"


def test_refuses_non_root(runtime):
    run, _, _ = runtime
    result = run(FAKE_UID="1026")
    assert result.returncode == 1
    assert "root" in result.stderr


def test_iowait_alerts_only_after_consecutive_runs(runtime):
    run, proc, state = runtime
    proc["stat_after"].write_text(cpu_line(10200, 900))  # 800/1000 = 80 %
    first = run()
    assert first.returncode == 0
    assert state.read_text() == "iowait_high_runs=1\n"
    second = run()
    assert second.returncode == 1
    assert "attente disque 80 % (seuil 40 %) depuis 2 exécutions" in second.stderr
    proc["stat_after"].write_text(cpu_line(10900, 200))
    assert run().returncode == 0
    assert state.read_text() == "iowait_high_runs=0\n"


def test_swap_and_memory_thresholds(runtime):
    run, proc, _ = runtime
    proc["meminfo"].write_text(MEMINFO.format(available=300000, swap_free=3000000))
    result = run()
    assert result.returncode == 1
    assert "swap occupé 3802 Mo (seuil 2048 Mo)" in result.stderr
    assert "mémoire disponible 292 Mo (seuil 500 Mo)" in result.stderr
    assert "2 alerte(s)" in result.stderr


def test_thresholds_are_configurable(runtime):
    run, _, _ = runtime
    result = run(SWAP_USED_MAX_MB="1")
    assert result.returncode == 1
    assert "swap occupé 618 Mo (seuil 1 Mo)" in result.stderr


def test_degraded_raid(runtime):
    run, proc, _ = runtime
    proc["mdstat"].write_text(MDSTAT_OK.replace("[4/4] [UUUU]\n\nmd3", "[4/3] [UU_U]\n\nmd3"))
    result = run()
    assert result.returncode == 1
    assert "RAID dégradé : md2 [UU_U]" in result.stderr
    assert "RAID dégradé ;" in result.stdout


@pytest.mark.parametrize(("overrides", "message", "state"), [
    ({"FAKE_EXEC_RC": "124"}, "ne répond pas en 10 s", "docker bloqué"),
    ({"FAKE_EXEC_RC": "1"}, "a échoué (code 1)", "docker erreur 1"),
    ({"FAKE_RUNNING": "absent", "FAKE_VERSION_RC": "124"}, "démon Docker ne répond pas", "docker bloqué"),
])
def test_docker_failures(runtime, overrides, message, state):
    run, _, _ = runtime
    result = run(**overrides)
    assert result.returncode == 1
    assert message in result.stderr
    assert state in result.stdout


@pytest.mark.parametrize(("running", "state"), [("false", "pihole arrêté"), ("absent", "pihole absent")])
def test_stopped_probe_is_not_an_alert(runtime, running, state):
    run, _, _ = runtime
    result = run(FAKE_RUNNING=running)
    assert result.returncode == 0, result.stderr
    assert f"docker {state}" in result.stdout


def test_missing_docker_is_an_alert(runtime, tmp_path):
    run, _, _ = runtime
    (tmp_path / "bin" / "docker").unlink()
    result = run()
    assert result.returncode == 1
    assert "commande docker introuvable" in result.stderr
    assert "docker introuvable" in result.stdout


def test_unreadable_proc_file(runtime, tmp_path):
    run, _, _ = runtime
    result = run(PROC_MDSTAT=str(tmp_path / "absent"))
    assert result.returncode == 1
    assert "fichier illisible" in result.stderr
