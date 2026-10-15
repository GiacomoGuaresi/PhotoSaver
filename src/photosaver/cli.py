"""Debug commands, to try the engine without the interface.

python -m photosaver.cli init  DISK --label A [--archive-dir Foto]
python -m photosaver.cli init  DISK --label B --join OTHER_DISK
python -m photosaver.cli scan  FOLDER
python -m photosaver.cli status DISK
python -m photosaver.cli check --disks A B [--full]
python -m photosaver.cli upload --disks A B --dest "FOTO 2026/MARE" FOLDER [--apply]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .core import archive, check, scanner, upload
from .core.disk import DiskError, open_disk

SHOWN = 10  # list items shown before "… and N more"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="photosaver.cli", description="PhotoSaver debug tools")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="make a folder a disk of a new or existing archive")
    init.add_argument("disk", type=Path)
    init.add_argument("--label", required=True)
    init.add_argument("--archive-dir", default="Foto", help="photo folder name (new archive)")
    init.add_argument("--join", type=Path, metavar="OTHER_DISK", help="join this disk's archive")

    scan = commands.add_parser("scan", help="list photos and videos in a folder")
    scan.add_argument("folder", type=Path)

    status = commands.add_parser("status", help="show a disk and its index")
    status.add_argument("disk", type=Path)

    up = commands.add_parser("upload", help="plan an upload, and apply it with --apply")
    up.add_argument("folders", type=Path, nargs="+")
    up.add_argument("--disks", type=Path, nargs="+", required=True)
    up.add_argument("--dest", help="archive folder (default: proposed)")
    up.add_argument("--apply", action="store_true", help="copy (default: only show the plan)")
    up.add_argument("--delete-sources", action="store_true", help="after a complete upload")

    chk = commands.add_parser("check", help="compare the disks with the index")
    chk.add_argument("--disks", type=Path, nargs="+", required=True)
    chk.add_argument("--full", action="store_true", help="read every file (bit rot)")

    args = parser.parse_args(argv)
    commands_ = {
        "init": _init,
        "scan": _scan,
        "status": _status,
        "upload": _upload,
        "check": _check,
    }
    try:
        return commands_[args.command](args)
    except (DiskError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _init(args) -> int:
    if args.join:
        disk = archive.join_archive(open_disk(args.join), args.disk, label=args.label)
    else:
        disk = archive.create_archive(args.disk, label=args.label, archive_dir=args.archive_dir)
    print(f"Disk {disk.label} ready: {disk.root}")
    print(f"  archive {disk.info.archive_id}, photos in {disk.archive}")
    return 0


def _scan(args) -> int:
    if not args.folder.is_dir():
        raise NotADirectoryError(f"{args.folder} is not a folder")
    result = scanner.scan(args.folder)
    kinds = Counter(entry.kind for entry in result.media)
    print(f"{len(result.media)} media files, {_size(result.size)}")
    for kind in (scanner.PHOTO, scanner.VIDEO, scanner.RAW):
        print(f"  {kind:6} {kinds[kind]}")
    _print_list("ignored (not photos or videos)", result.ignored)
    _print_list("skipped (hidden or system)", result.skipped)
    _print_list("unreadable", [f"{path}: {reason}" for path, reason in result.errors])
    return 0


def _status(args) -> int:
    disk = open_disk(args.disk)
    print(f"Disk {disk.label} ({disk.id})")
    print(f"  archive  {disk.info.archive_id}")
    print(f"  photos   {disk.archive}")
    with archive.open_index(disk) as index:
        count, size = index.count_files()
        print(f"  index    revision {index.revision}, schema {index.schema_version}")
        print(f"  files    {count}, {_size(size)}")
        print("  disks    " + ", ".join(f"{d.label} ({d.id[:8]})" for d in index.disks()))
        print("Recent events:")
        for event in index.events(limit=SHOWN):
            where = f" {event.path}" if event.path else ""
            print(f"  {event.at}  {event.kind}{where}")
    return 0


def _upload(args) -> int:
    with archive.Archive.open([open_disk(path) for path in args.disks]) as arch:
        plan = upload.analyze(args.folders)
        top = upload.top_level_folders(arch)
        for folder in plan.folders:
            folder.destination = (
                args.dest if args.dest is not None else (upload.propose_destination(folder, top))
            )
        upload.resolve(plan, arch)
        for folder in plan.folders:
            print(f"{folder.source.name}  →  {folder.destination or '(archive root)'}")
            statuses = Counter(item.status for item in folder.items)
            print("  " + ", ".join(f"{n} {status}" for status, n in sorted(statuses.items())))
            if folder.ignored:
                print(f"  {len(folder.ignored)} ignored (not photos or videos)")
        for item in plan.items:
            if item.status in (upload.CONFLICT, upload.DUPLICATE):
                print(f"  {item.status}: {item.relative} → {item.action} {item.target}")
        print(f"To copy: {len(plan.to_copy())} files, {_size(plan.copy_size)}")
        if not args.apply:
            return 0

        result = upload.apply(plan, arch)
        print(f"Copied and verified on {len(arch.disks)} disks: {len(result.copied)} files")
        for item, reason in result.failed:
            print(f"  failed: {item.relative}: {reason}")
        if args.delete_sources and not result.failed:
            cleanup = upload.delete_sources(plan, arch)
            print(f"Deleted {len(cleanup.deleted)} originals, kept {len(cleanup.kept)}")
        return 1 if result.failed else 0


def _check(args) -> int:
    with archive.Archive.open([open_disk(path) for path in args.disks]) as arch:
        if arch.missing:
            print(f"Not connected: {', '.join(arch.missing)}")
        report = (check.full_check if args.full else check.quick_check)(arch)
        labels = {disk.id: disk.label for disk in arch.disks}
        print(f"{report.files} files in the index, {len(report.differences)} differences")
        for diff in sorted(report.differences, key=lambda d: (d.kind, d.path, labels[d.disk_id])):
            print(f"  {diff.kind:9} {labels[diff.disk_id]}  {diff.path}")
        for disk_id, path, reason in report.errors:
            print(f"  error     {labels[disk_id]}  {path}: {reason}")
        return 0 if report.clean else 1


def _print_list(title: str, items: list[str]) -> None:
    if not items:
        return
    print(f"{len(items)} {title}:")
    for item in items[:SHOWN]:
        print(f"  {item}")
    if len(items) > SHOWN:
        print(f"  … and {len(items) - SHOWN} more")


def _size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000
    return f"{size:.1f} TB"


if __name__ == "__main__":
    sys.exit(main())
