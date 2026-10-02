# Python Automation Suite

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Modules](https://img.shields.io/badge/Modules-4-orange)
![Scheduler](https://img.shields.io/badge/Scheduler-schedule-purple)

A four-tool Python automation suite featuring a duplicate-file cleaner,
backup & file-monitoring system, platform surveillance, and process logger.

---

## Project Structure

```
python automation project/
├── main.py                   ← CLI launcher (run this)
├── config.py                 ← All settings in one place
├── utils.py                  ← Shared helpers (logging, hashing, formatting)
├── file_cleaner.py           ← Module 1 — Duplicate-file cleaner
├── backup_monitor.py         ← Module 2 — Backup & file monitor
├── system_surveillance.py    ← Module 3 — Platform surveillance
├── process_logger.py         ← Module 4 — Process logger
├── requirements.txt
├── logs/                     ← Auto-created; all log files written here
│   ├── cleaner.log
│   ├── backup_monitor.log
│   ├── system_surveillance.log
│   └── process_logger.log
└── backups/                  ← Auto-created; ZIP archives stored here
```

---

## Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Run all four tools together

```bash
python main.py all
```

### 3 — Run individual tools

```bash
python main.py cleaner           # Duplicate-file cleaner only
python main.py backup            # Backup & monitor only
python main.py surveillance      # System surveillance only
python main.py process           # Process logger only
```

### 4 — Combine any tools

```bash
python main.py cleaner backup
python main.py surveillance process
```

### 5 — Run once (no loop)

```bash
python main.py --once all
python main.py --once cleaner backup
```

### 6 — Override the interval

```bash
# cleaner/backup → minutes  |  surveillance/process → seconds
python main.py --interval 5 surveillance
python main.py --interval 15 process
```

### 7 — Check log status

```bash
python main.py status
```

---

## Tool Details

### Module 1 — Duplicate-File Cleaner (`file_cleaner.py`)
- Recursively scans the project directory.
- Groups files by **MD5 checksum**.
- Keeps the oldest file; moves duplicates to `.quarantine/`.
- Appends a formatted report to `logs/cleaner.log` after each run.
- Configurable scan interval via `config.CLEANER_SCHEDULE_MINS`.

### Module 2 — Backup & File Monitor (`backup_monitor.py`)
- Computes MD5 of every file on each run and compares against a persisted
  JSON snapshot (`backups/.file_state.json`).
- Detects **added**, **modified**, and **deleted** files.
- Creates a timestamped **ZIP archive** of the entire directory.
- **Rotates old archives** — keeps only the last N (configurable).
- Logs all events to `logs/backup_monitor.log`.

### Module 3 — System Surveillance (`system_surveillance.py`)
- Captures: **CPU** (per-core + overall + frequency), **RAM + swap**,
  **disk** partitions (usage / read / write), **network** I/O counters,
  **battery**, and **platform** info.
- Fires **threshold alerts** (configurable %) to the log if any metric spikes.
- Writes a tabular snapshot to `logs/system_surveillance.log` every tick.

### Module 4 — Process Logger (`process_logger.py`)
- Enumerates all running processes via `psutil`.
- Records **PID, name, username, CPU%, RSS, VMS, status, start time**.
- Logs the top-N processes (configurable; default 15) sorted by memory, CPU, or PID.
- Writes timestamped snapshots to `logs/process_logger.log`.

---

## Configuration (`config.py`)

| Setting                  | Default      | Description                              |
|--------------------------|--------------|------------------------------------------|
| `CLEANER_SCHEDULE_MINS`  | `60`         | Cleaner run interval (minutes)           |
| `MONITOR_SCHEDULE_MINS`  | `30`         | Backup run interval (minutes)            |
| `MONITOR_ARCHIVE_KEEP`   | `5`          | Max backup archives to retain            |
| `SURV_SCHEDULE_SECS`     | `60`         | Surveillance snapshot interval (seconds) |
| `SURV_CPU_ALERT_PCT`     | `85.0`       | CPU alert threshold (%)                  |
| `SURV_RAM_ALERT_PCT`     | `85.0`       | RAM alert threshold (%)                  |
| `SURV_DISK_ALERT_PCT`    | `90.0`       | Disk alert threshold (%)                 |
| `PROC_SCHEDULE_SECS`     | `30`         | Process snapshot interval (seconds)      |
| `PROC_TOP_N`             | `15`         | Processes shown per snapshot             |
| `PROC_SORT_BY`           | `"memory"`   | Sort key: `memory` / `cpu` / `pid`      |

---

## Tech Stack

| Library    | Purpose                                      |
|------------|----------------------------------------------|
| `os`       | Path manipulation, directory walking         |
| `hashlib`  | MD5 checksum computation                     |
| `shutil`   | File moves, ZIP archive creation             |
| `psutil`   | CPU, RAM, disk, network, process metrics     |
| `schedule` | Pure-Python job scheduling                   |
| `colorama` | Cross-platform coloured console output       |
| `tabulate` | Pretty-printed tables in logs & console      |

---

## Key Features

- **MD5-based change detection** — only flags genuinely new/modified files.
- **Quarantine, not deletion** — duplicates are moved, never permanently lost.
- **Archive rotation** — disk space is managed automatically.
- **Threshold alerting** — warnings written to log when CPU/RAM/disk spikes.
- **Thread-safe, daemon threads** — all tools run concurrently from one process.
- **Single config file** — every path and interval in `config.py`.
- **Coloured console output** — via `colorama`, works on Windows/macOS/Linux.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full details.

```
MIT License  Copyright (c) 2026 Prithviraj
```

You are free to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of this software with proper attribution.
