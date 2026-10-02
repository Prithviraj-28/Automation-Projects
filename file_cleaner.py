"""
file_cleaner.py -- Module 1: Duplicate-File Cleaner
====================================================
Scans a target directory recursively, groups files by their MD5 checksum,
keeps the *oldest* copy of each group, and moves all duplicates to a
quarantine sub-folder.  A detailed log is generated after every run.

Schedule: configurable via config.CLEANER_SCHEDULE_MINS
"""

import os
import shutil
import schedule
import time
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate

import config
from utils import get_logger, md5_of_file, bytes_to_human, timestamp, section

logger = get_logger("FileCleaner", config.CLEANER_LOG_FILE)

# Quarantine folder sits inside the scan directory
QUARANTINE_DIR = os.path.join(config.CLEANER_SCAN_DIR, ".quarantine")


# --- Core Logic ---------------------------------------------------------------

def _collect_files(directory: str) -> list[str]:
    """Walk *directory* and return a list of all file paths (skip quarantine)."""
    collected = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden/quarantine folders
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            collected.append(os.path.join(root, fname))
    return collected


def _group_by_hash(file_paths: list[str]) -> dict[str, list[str]]:
    """Return a mapping of MD5 → [file_paths] for files that share a hash."""
    hash_map: dict[str, list[str]] = defaultdict(list)
    for path in file_paths:
        digest = md5_of_file(path)
        if digest:
            hash_map[digest].append(path)
    # Only keep groups with actual duplicates
    return {k: v for k, v in hash_map.items() if len(v) > 1}


def _quarantine_duplicates(groups: dict[str, list[str]]) -> list[dict]:
    """
    For each duplicate group keep the oldest file, quarantine the rest.
    Returns a list of action-dicts for the report.
    """
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    actions = []
    for digest, paths in groups.items():
        # Sort by creation/modification time -- keep the earliest
        paths.sort(key=lambda p: os.path.getmtime(p))
        kept = paths[0]
        for dup in paths[1:]:
            dest_name = f"{timestamp()}_{os.path.basename(dup)}"
            dest = os.path.join(QUARANTINE_DIR, dest_name)
            try:
                shutil.move(dup, dest)
                size = os.path.getsize(dest)
                actions.append({
                    "status":    "MOVED",
                    "duplicate": dup,
                    "kept":      kept,
                    "hash":      digest[:12] + "...",
                    "size":      bytes_to_human(size),
                })
                logger.info("Quarantined %-60s → %s", dup, dest_name)
            except Exception as exc:
                actions.append({
                    "status":    "ERROR",
                    "duplicate": dup,
                    "kept":      kept,
                    "hash":      digest[:12] + "...",
                    "size":      "--",
                })
                logger.error("Failed to move %s: %s", dup, exc)
    return actions


def _write_report(actions: list[dict], scan_dir: str) -> None:
    """Append a formatted run-report to the cleaner log file."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        [a["status"], os.path.basename(a["duplicate"]), a["size"], a["hash"]]
        for a in actions
    ]
    table = tabulate(
        rows,
        headers=["Status", "File", "Size", "MD5 (partial)"],
        tablefmt="rounded_outline",
    ) if rows else "  No duplicates found -- directory is clean."

    report_lines = [
        section(f"CLEANER REPORT  --  {now}"),
        f"  Scan directory : {scan_dir}",
        f"  Quarantine dir : {QUARANTINE_DIR}",
        f"  Duplicates removed : {len(actions)}",
        "",
        table,
        "",
    ]
    with open(config.CLEANER_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")


# --- Main Job -----------------------------------------------------------------

def run_cleaner(scan_dir: str = config.CLEANER_SCAN_DIR) -> None:
    """Full scan-and-clean cycle."""
    logger.info(">>  Cleaner started -- scanning: %s", scan_dir)
    files  = _collect_files(scan_dir)
    logger.info("   Found %d files", len(files))

    groups = _group_by_hash(files)
    dup_count = sum(len(v) - 1 for v in groups.values())
    logger.info("   Duplicate groups: %d  |  Files to remove: %d", len(groups), dup_count)

    actions = _quarantine_duplicates(groups)
    _write_report(actions, scan_dir)

    if actions:
        logger.info("[OK]  Cleaner done -- %d duplicate(s) quarantined.", len(actions))
    else:
        logger.info("[OK]  Cleaner done -- directory is already clean.")


# --- Scheduler Entry Point ----------------------------------------------------

def start_scheduled(interval_mins: int = config.CLEANER_SCHEDULE_MINS) -> None:
    """Run immediately, then schedule repeating execution."""
    run_cleaner()
    schedule.every(interval_mins).minutes.do(run_cleaner)
    logger.info("[TIMER]  Cleaner scheduled every %d minute(s).", interval_mins)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduled()
