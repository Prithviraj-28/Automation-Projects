"""
backup_monitor.py -- Module 2: Backup & File Monitoring System
=============================================================
Watches a directory for new or modified files (via MD5 comparison),
creates timestamped ZIP archives, rotates old archives, and logs every
event.  A full backup is performed on every scheduled run.

Schedule: configurable via config.MONITOR_SCHEDULE_MINS
"""

import os
import shutil
import json
import zipfile
import schedule
import time
from datetime import datetime
from pathlib import Path
from tabulate import tabulate

import config
from utils import get_logger, md5_of_file, bytes_to_human, timestamp, section

logger = get_logger("BackupMonitor", config.MONITOR_LOG_FILE)

# State file -- persists MD5 snapshots between runs
STATE_FILE = os.path.join(config.MONITOR_BACKUP_DIR, ".file_state.json")


# --- State Persistence --------------------------------------------------------

def _load_state() -> dict[str, str]:
    """Load the previous MD5 snapshot from disk (path → md5)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict[str, str]) -> None:
    """Persist the current MD5 snapshot to disk."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# --- File Discovery -----------------------------------------------------------

def _scan_directory(directory: str) -> dict[str, str]:
    """Walk *directory* and return a {path: md5} mapping."""
    snapshot: dict[str, str] = {}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            full = os.path.join(root, fname)
            # Skip state file and backup archives themselves
            if full == STATE_FILE or full.endswith(".zip"):
                continue
            digest = md5_of_file(full)
            if digest:
                snapshot[full] = digest
    return snapshot


# --- Change Detection ---------------------------------------------------------

def _detect_changes(old: dict[str, str], new: dict[str, str]) -> dict:
    """
    Compare two snapshots and return categorised changes:
      added, modified, deleted
    """
    added    = [p for p in new if p not in old]
    deleted  = [p for p in old if p not in new]
    modified = [p for p in new if p in old and new[p] != old[p]]
    return {"added": added, "modified": modified, "deleted": deleted}


# --- Backup / Archive ---------------------------------------------------------

def _create_archive(watch_dir: str, backup_dir: str) -> str:
    """ZIP the entire watch directory and return the archive path."""
    os.makedirs(backup_dir, exist_ok=True)
    archive_name = f"backup_{timestamp()}.zip"
    archive_path = os.path.join(backup_dir, archive_name)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(watch_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                fp = os.path.join(root, fname)
                if fp == STATE_FILE or fp.endswith(".zip"):
                    continue
                arcname = os.path.relpath(fp, watch_dir)
                zf.write(fp, arcname)

    size = os.path.getsize(archive_path)
    logger.info("Archive created: %s  (%s)", archive_name, bytes_to_human(size))
    return archive_path


def _rotate_archives(backup_dir: str, keep: int = config.MONITOR_ARCHIVE_KEEP) -> None:
    """Delete the oldest archives beyond the *keep* limit."""
    archives = sorted(
        Path(backup_dir).glob("backup_*.zip"),
        key=lambda p: p.stat().st_mtime,
    )
    for old in archives[:-keep]:
        try:
            old.unlink()
            logger.info("Rotated old archive: %s", old.name)
        except OSError as exc:
            logger.warning("Could not delete %s: %s", old.name, exc)


# --- Report -------------------------------------------------------------------

def _write_report(changes: dict, archive_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for status, paths in [("ADDED", changes["added"]),
                          ("MODIFIED", changes["modified"]),
                          ("DELETED", changes["deleted"])]:
        for p in paths:
            size = bytes_to_human(os.path.getsize(p)) if os.path.exists(p) else "--"
            rows.append([status, os.path.basename(p), size, os.path.dirname(p)])

    table = tabulate(
        rows,
        headers=["Event", "File", "Size", "Directory"],
        tablefmt="rounded_outline",
    ) if rows else "  No file changes detected since last run."

    total = sum(len(v) for v in changes.values())
    report = [
        section(f"BACKUP MONITOR REPORT  --  {now}"),
        f"  Watch directory : {config.MONITOR_WATCH_DIR}",
        f"  Archive created : {os.path.basename(archive_path)}",
        f"  Total changes   : {total}  "
        f"(+{len(changes['added'])} / ~{len(changes['modified'])} / -{len(changes['deleted'])})",
        "",
        table,
        "",
    ]
    with open(config.MONITOR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")


# --- Main Job -----------------------------------------------------------------

def run_backup_monitor(
    watch_dir:  str = config.MONITOR_WATCH_DIR,
    backup_dir: str = config.MONITOR_BACKUP_DIR,
) -> None:
    logger.info(">>  Backup monitor started")

    old_state = _load_state()
    new_state = _scan_directory(watch_dir)
    changes   = _detect_changes(old_state, new_state)

    total = sum(len(v) for v in changes.values())
    logger.info(
        "   Changes -- added: %d | modified: %d | deleted: %d",
        len(changes["added"]), len(changes["modified"]), len(changes["deleted"]),
    )

    archive = _create_archive(watch_dir, backup_dir)
    _rotate_archives(backup_dir)
    _save_state(new_state)
    _write_report(changes, archive)

    logger.info("[OK]  Backup monitor done  (archive: %s)", os.path.basename(archive))


# --- Scheduler Entry Point ----------------------------------------------------

def start_scheduled(interval_mins: int = config.MONITOR_SCHEDULE_MINS) -> None:
    run_backup_monitor()
    schedule.every(interval_mins).minutes.do(run_backup_monitor)
    logger.info("[TIMER]  Backup monitor scheduled every %d minute(s).", interval_mins)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduled()
