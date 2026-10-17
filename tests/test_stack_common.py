"""Le helper préserve la sélection Compose et transmet le fichier .env."""

import os
from pathlib import Path
import shutil
import subprocess


def test_compose_selection_is_not_overwritten(tmp_path):
    source = Path(__file__).resolve().parents[1] / "scripts/lib/stack-common.sh"
    helper = tmp_path / "scripts/lib/stack-common.sh"
    helper.parent.mkdir(parents=True)
    shutil.copyfile(source, helper)
    stack = tmp_path / "compose/sample"
    stack.mkdir(parents=True)
    (stack / "compose.yaml").write_text("services: {}\n")
    (stack / ".env").write_text("COMPOSE_FILE=compose.yaml:compose.openai.yaml\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('''#!/bin/sh
if [ "$1" = "info" ]; then exit 0; fi
printf '%s\\n' "$COMPOSE_FILE" "$PWD" "$@" > "$CAPTURE"
''')
    docker.chmod(0o755)
    capture = tmp_path / "capture"
    selected = "compose.yaml:compose.openai.yaml"
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
           "COMPOSE_FILE": selected, "CAPTURE": str(capture)}
    subprocess.run(["bash", "-c", 'source "$1"; init_stack sample; compose config --quiet',
                    "test", str(helper)], env=env, check=True, capture_output=True)
    assert capture.read_text().splitlines() == [
        selected, str(stack), "compose", "--env-file", str(stack / ".env"), "config", "--quiet",
    ]
