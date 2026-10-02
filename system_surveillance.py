"""
system_surveillance.py -- Module 3: Platform Surveillance System
================================================================
Captures a full system snapshot at every tick:
  * CPU usage (per-core + overall)
  * RAM utilisation
  * Disk partitions (usage, read/write)
  * Network I/O (bytes sent/received, error counters)
  * Battery (if available)
  * Platform information

Alerts are written to the log whenever any threshold is exceeded.

Schedule: configurable via config.SURV_SCHEDULE_SECS
"""

import os
import platform
import time
import schedule
import psutil
from datetime import datetime
from tabulate import tabulate

import config
from utils import get_logger, bytes_to_human, section

logger = get_logger("SystemSurveillance", config.SURV_LOG_FILE)


# --- Snapshot Collectors ------------------------------------------------------

def _cpu_snapshot() -> dict:
    per_core = psutil.cpu_percent(interval=1, percpu=True)
    overall  = psutil.cpu_percent(interval=None)
    freq     = psutil.cpu_freq()
    return {
        "overall":  overall,
        "per_core": per_core,
        "freq_mhz": round(freq.current, 1) if freq else "N/A",
        "cores":    psutil.cpu_count(logical=True),
    }


def _ram_snapshot() -> dict:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total":      vm.total,
        "used":       vm.used,
        "available":  vm.available,
        "percent":    vm.percent,
        "swap_total": sw.total,
        "swap_used":  sw.used,
        "swap_pct":   sw.percent,
    }


def _disk_snapshot() -> list[dict]:
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        partitions.append({
            "device":     part.device,
            "mountpoint": part.mountpoint,
            "fstype":     part.fstype,
            "total":      usage.total,
            "used":       usage.used,
            "free":       usage.free,
            "percent":    usage.percent,
        })
    return partitions


def _network_snapshot() -> dict:
    counters = psutil.net_io_counters()
    return {
        "bytes_sent":   counters.bytes_sent,
        "bytes_recv":   counters.bytes_recv,
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
        "errin":        counters.errin,
        "errout":       counters.errout,
        "dropin":       counters.dropin,
        "dropout":      counters.dropout,
    }


def _battery_snapshot() -> dict | None:
    bat = psutil.sensors_battery()
    if bat is None:
        return None
    return {
        "percent":    bat.percent,
        "plugged_in": bat.power_plugged,
        "secs_left":  bat.secsleft,
    }


def _platform_info() -> dict:
    uname = platform.uname()
    return {
        "system":    uname.system,
        "node":      uname.node,
        "release":   uname.release,
        "machine":   uname.machine,
        "processor": uname.processor,
        "python":    platform.python_version(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
    }


# --- Alert Check -------------------------------------------------------------

def _check_alerts(cpu: dict, ram: dict, disks: list[dict]) -> list[str]:
    alerts = []
    if cpu["overall"] >= config.SURV_CPU_ALERT_PCT:
        alerts.append(f"[WARN]  CPU usage at {cpu['overall']}%  (threshold {config.SURV_CPU_ALERT_PCT}%)")
    if ram["percent"] >= config.SURV_RAM_ALERT_PCT:
        alerts.append(f"[WARN]  RAM usage at {ram['percent']}%  (threshold {config.SURV_RAM_ALERT_PCT}%)")
    for d in disks:
        if d["percent"] >= config.SURV_DISK_ALERT_PCT:
            alerts.append(
                f"[WARN]  Disk {d['mountpoint']} at {d['percent']}%  "
                f"(threshold {config.SURV_DISK_ALERT_PCT}%)"
            )
    return alerts


# --- Report Builder ----------------------------------------------------------

def _build_report(cpu, ram, disks, net, bat, plat, alerts) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [section(f"SYSTEM SURVEILLANCE  --  {now}")]

    # Platform
    plat_rows = [[k.capitalize(), v] for k, v in plat.items()]
    lines.append("\n-- Platform --")
    lines.append(tabulate(plat_rows, tablefmt="simple"))

    # CPU
    core_rows = [[f"Core {i}", f"{pct}%"] for i, pct in enumerate(cpu["per_core"])]
    lines.append(f"\n-- CPU  (overall {cpu['overall']}%  |  {cpu['freq_mhz']} MHz  |  {cpu['cores']} logical cores) --")
    lines.append(tabulate(core_rows, headers=["Core", "Usage"], tablefmt="simple"))

    # RAM
    lines.append("\n-- Memory --")
    ram_rows = [
        ["Total",      bytes_to_human(ram["total"])],
        ["Used",       bytes_to_human(ram["used"])],
        ["Available",  bytes_to_human(ram["available"])],
        ["Usage %",    f"{ram['percent']}%"],
        ["Swap Total", bytes_to_human(ram["swap_total"])],
        ["Swap Used",  bytes_to_human(ram["swap_used"])],
        ["Swap %",     f"{ram['swap_pct']}%"],
    ]
    lines.append(tabulate(ram_rows, tablefmt="simple"))

    # Disk
    lines.append("\n-- Disk Partitions --")
    disk_rows = [
        [d["mountpoint"], d["fstype"],
         bytes_to_human(d["total"]), bytes_to_human(d["used"]),
         bytes_to_human(d["free"]),  f"{d['percent']}%"]
        for d in disks
    ]
    lines.append(tabulate(disk_rows,
                          headers=["Mount", "FS", "Total", "Used", "Free", "%"],
                          tablefmt="rounded_outline"))

    # Network
    lines.append("\n-- Network I/O --")
    net_rows = [
        ["Bytes Sent",    bytes_to_human(net["bytes_sent"])],
        ["Bytes Recv",    bytes_to_human(net["bytes_recv"])],
        ["Packets Sent",  net["packets_sent"]],
        ["Packets Recv",  net["packets_recv"]],
        ["Errors In",     net["errin"]],
        ["Errors Out",    net["errout"]],
        ["Dropped In",    net["dropin"]],
        ["Dropped Out",   net["dropout"]],
    ]
    lines.append(tabulate(net_rows, tablefmt="simple"))

    # Battery
    if bat:
        lines.append("\n-- Battery --")
        secs = bat["secs_left"]
        time_left = (
            "Charging / AC"
            if secs == psutil.POWER_TIME_UNLIMITED
            else (f"{secs//3600}h {(secs%3600)//60}m" if secs > 0 else "Unknown")
        )
        bat_rows = [
            ["Charge %",   f"{bat['percent']}%"],
            ["Plugged In",  bat["plugged_in"]],
            ["Time Left",   time_left],
        ]
        lines.append(tabulate(bat_rows, tablefmt="simple"))

    # Alerts
    if alerts:
        lines.append("\n-- [WARN]  ALERTS --")
        lines.extend(alerts)

    lines.append("")
    return "\n".join(lines)


# --- Main Job -----------------------------------------------------------------

def run_surveillance() -> None:
    logger.info(">>  Taking system snapshot ...")
    cpu   = _cpu_snapshot()
    ram   = _ram_snapshot()
    disks = _disk_snapshot()
    net   = _network_snapshot()
    bat   = _battery_snapshot()
    plat  = _platform_info()

    alerts = _check_alerts(cpu, ram, disks)
    for alert in alerts:
        logger.warning(alert)

    report = _build_report(cpu, ram, disks, net, bat, plat, alerts)
    with open(config.SURV_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(report + "\n")

    logger.info(
        "[OK]  Snapshot written  |  CPU %.1f%%  |  RAM %.1f%%  |  %d alert(s)",
        cpu["overall"], ram["percent"], len(alerts),
    )


# --- Scheduler Entry Point ----------------------------------------------------

def start_scheduled(interval_secs: int = config.SURV_SCHEDULE_SECS) -> None:
    run_surveillance()
    schedule.every(interval_secs).seconds.do(run_surveillance)
    logger.info("[TIMER]  Surveillance scheduled every %d second(s).", interval_secs)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    start_scheduled()
