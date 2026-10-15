# PhotoSaver

[![CI](https://github.com/GiacomoGuaresi/PhotoSaver/actions/workflows/ci.yml/badge.svg)](https://github.com/GiacomoGuaresi/PhotoSaver/actions/workflows/ci.yml)

A small desktop app that keeps a photo archive **mirrored on two external
drives**, like RAID 1 but at application level: both drives stay plain exFAT
disks, readable on any computer even without the app.

- **Upload** folders of photos and videos to both drives in one go, with
  every copy verified by checksum.
- **Check** that the two drives hold the same files, detect silent corruption
  (bit rot), missing, moved or deleted files, and fix them from the good copy.
- **Track changes**, also those made outside the app, with a full history and
  an app-level trash.
- **Browse** the archive with thumbnails, full-screen preview and per-file sync
  status.

> **Status:** early development. See the [roadmap](doc/roadmap.md).

Made for people who barely use a computer: big buttons, one step at a time, no
technical words, Italian and English.

## Try it

With [uv](https://docs.astral.sh/uv/), on two simulated disks (plain folders):

```sh
uv run python scripts/dev_disks.py setup      # fake photos, an archive on two folders
uv run python -m photosaver --disks dev-disks/disk-a dev-disks/disk-b
uv run python scripts/dev_disks.py break all  # then "Check the disks" in the app
```

Built with Python and PySide6, for Linux and Windows (macOS later).
Design documents are in [`doc/`](doc/README.md) (in Italian).

## License

[MIT](LICENSE)
