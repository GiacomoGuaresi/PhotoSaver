"""Create or reset the simulated disks used during development (see doc/sviluppo.md).

uv run python scripts/dev_disks.py create [--root dev-disks] [--seed 0] [--scale 1]
uv run python scripts/dev_disks.py reset  [--root dev-disks]
"""

import argparse
from pathlib import Path

from photosaver.devtools import dev_disks

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "dev-disks"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["create", "reset"])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--scale", type=int, default=1, help="multiply the number of photos")
    args = parser.parse_args()

    if args.command == "reset":
        dev_disks.reset(args.root)
        print(f"Removed {args.root}")
        return

    counts = dev_disks.create(args.root, seed=args.seed, scale=args.scale)
    print(f"Created {args.root}")
    print(", ".join(f"{n} {kind}" for kind, n in counts.items()))


if __name__ == "__main__":
    main()
