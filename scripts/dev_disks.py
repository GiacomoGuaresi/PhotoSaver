"""Create, set up and break the simulated disks used during development (doc/sviluppo.md).

uv run python scripts/dev_disks.py create  [--seed 0] [--scale 1]   empty disks + desktop
uv run python scripts/dev_disks.py setup   [--seed 0]               + archive on A and B
uv run python scripts/dev_disks.py break   corrupt move … | all      failure scenarios
uv run python scripts/dev_disks.py reset
"""

import argparse
from pathlib import Path

from photosaver.devtools import dev_disks

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "dev-disks"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["create", "setup", "break", "reset"])
    parser.add_argument("scenarios", nargs="*", help=f"for break: {', '.join(dev_disks.SCENARIOS)}")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--scale", type=int, default=1, help="multiply the number of photos")
    args = parser.parse_args()

    if args.command == "reset":
        dev_disks.reset(args.root)
        print(f"Removed {args.root}")
    elif args.command == "create":
        counts = dev_disks.create(args.root, seed=args.seed, scale=args.scale)
        print(f"Created {args.root}")
        print(", ".join(f"{n} {kind}" for kind, n in counts.items()))
    elif args.command == "setup":
        dev_disks.setup(args.root, seed=args.seed)
        print(f"Created {args.root} with an archive on disk-a and disk-b")
    else:
        names = list(dev_disks.SCENARIOS) if args.scenarios in ([], ["all"]) else args.scenarios
        unknown = set(names) - set(dev_disks.SCENARIOS)
        if unknown:
            parser.error(f"unknown scenarios: {', '.join(sorted(unknown))}")
        for done in dev_disks.break_disks(args.root, names, seed=args.seed):
            print(done)


if __name__ == "__main__":
    main()
