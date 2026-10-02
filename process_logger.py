"""
process_logger.py -- Module 4: Process Logger
=============================================
Captures periodic snapshots of all running processes, recording:
  * PID, name, username/owner
  * CPU % and memory (RSS + VMS)
  * Status, creation time, command line

Top-N processes (by memory or CPU) are highlighted in the log.
Logs are written to a timestamped file every tick.

Schedule: configurable via config.PROC_SCHEDULE_SECS
"""

import os
import time
import schedule
import psutil
from datetime import datetime
from tabulate import tabulate

import config
from utils import get_logger, bytes_to_human, section

logger = get_logger("ProcessLogger", config.PROC_LOG_FILE)

_SORT_KEYS = {
    "memory": lambda p: p.get("rss", 0),
    "cpu":    lambda p: p.get("cpu_pct", 0.0),
    "pid":    lambda p: p.get("pid", 0),
}


# --- Process Snapshot --------------------------------------------------------

def _snapshot_processes() -> list[dict]:
    """Return a list of info-dicts for every accessible running process."""
    procs = []
    for proc in psutil.process_iter(
        ["pid", "name", "username", "status",
         "cpu_percent", "memory_info", "create_time", "cmdline"]
    ):
        try:
            info = proc.info
            mem  = info.get("memory_info") or psutil._common.pmem(0, 0)
            procs.append({
                "pid":      info["pid"],
                "name":     info["name"] or "--",
                "user":     info.get("username") or "--",
                "status":   info.get("status", "--"),
                "cpu_pct":  info.get("cpu_percent", 0.0) or 0.0,
                "rss":      mem.rss,
                "vms":      mem.vms,
                "created":  datetime.fromtimestamp(
                                info["create_time"]
                            ).strftime("%H:%M:%S") if info.get("create_time") else "--",
                "cmdline":  " ".join(info.get("cmdline") or [])[:80],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return procs


# --- Summary Statistics -------------------------------------------------------

def _compute_summary(procs: list[dict]) -> dict:
    total_rss = sum(p["rss"] for p in procs)
    running   = sum(1 for p in procs if p["status"] == "running")
    sleeping  = sum(1 for p in procs if p["status"] == "sleeping")
    zombie    = sum(1 for p in procs if p["status"] == "zombie")
    return {
        "total":      len(procs),
        "running":    running,
        "sleeping":   sleeping,
        "zombie":     zombie,
        "total_rss":  total_rss,
    }


# --- Report Builder ----------------------------------------------------------

def _build_report(procs: list[dict], top_n: int, sort_by: str) -> str:
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = _compute_summary(procs)

    sort_fn = _SORT_KEYS.get(sort_by, _SORT_KEYS["memory"])
    top     = sorted(procs, key=sort_fn, reverse=True)[:top_n]

    rows = [
        [
            p["pid"],
            p["name"][:28],
            p["user"][:20],
            f"{p['cpu_pct']:.1f}%",
            bytes_to_human(p["rss"]),
            bytes_to_human(p["vms"]),
            p["status"],
            p["created"],
        ]
        for p in top
    ]

    table = tabulate(
        rows,
        headers=["PID", "Name", "User", "CPU%", "RSS", "VMS", "Status", "Started"],
        tablefmt="rounded_outline",
    )

    lines = [
        section(f"PROCESS LOGGER  --  {now}"),
        f"  Total processes : {summary['total']}",
        f"  Running         : {summary['running']}",
        f"  Sleeping        : {summary['sleeping']}",
        f"  Zombie          : {summary['zombie']}",
        f"  Total RSS       : {bytes_to_human(summary['total_rss'])}",
        f"  Showing top {top_n} by {sort_by.upper()}",
        "",
        table,
        "",
    ]
    return "\n".join(lines)


# --- Main Job -----------------------------------------------------------------

def run_process_logger(
    top_n:   int = config.PROC_TOP_N,
    sort_by: str = config.PROC_SORT_BY,
) -> None:
    logger.info(">>  Taking process snapshot ...")
    procs = _snapshot_processes()

    report = _build_report(procs, top_n, sort_by)
    with open(config.PROC_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(report + "\n")

    summary = _compute_summary(procs)
    logger.info(
        "[OK]  Snapshot written  |  Processes: %d  |  Running: %d  |  RSS: %s",
        summary["total"], summary["running"], bytes_to_human(summary["total_rss"]),
    )


# --- Scheduler Entry Point ----------------------------------------------------

def start_scheduled(
    interval_secs: int = config.PROC_SCHEDULE_SECS,
    top_n:         int = config.PROC_TOP_N,
    sort_by:       str = config.PROC_SORT_BY,
) -> None:
    run_process_logger(top_n, sort_by)
    schedule.every(interval_secs).seconds.do(run_process_logger, top_n=top_n, sort_by=sort_by)
    logger.info("[TIMER]  Process logger scheduled every %d second(s).", interval_secs)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduled()
