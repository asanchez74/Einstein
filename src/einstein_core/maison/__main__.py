"""Validation d'un catalogue avant remplacement ou déploiement."""

import argparse
from pathlib import Path
import sys

from einstein_core.maison.inventory import InventoryError, load_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valider un inventaire Einstein Maison")
    parser.add_argument("catalogue", type=Path, help="Chemin du fichier JSON")
    args = parser.parse_args(argv)
    try:
        items = load_inventory(args.catalogue)
    except InventoryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Inventaire valide : {len(items)} équipement(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
