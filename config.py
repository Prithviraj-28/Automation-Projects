"""
config.py -- Centralized configuration for the Python Automation Suite.
All modules import their settings from here.
"""

import os

# --- Base Directories --------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR   = os.path.join(BASE_DIR, "logs")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# Auto-create required directories
for _d in (LOGS_DIR, BACKUP_DIR):
    os.makedirs(_d, exist_ok=True)

# --- File Cleaner -------------------------------------------------------------
CLEANER_SCAN_DIR      = BASE_DIR          # Directory to scan for duplicates
CLEANER_LOG_FILE      = os.path.join(LOGS_DIR, "cleaner.log")
CLEANER_SCHEDULE_MINS = 60               # How often to run (minutes)

# --- Backup & File Monitor ----------------------------------------------------
MONITOR_WATCH_DIR      = BASE_DIR
MONITOR_BACKUP_DIR     = BACKUP_DIR
MONITOR_LOG_FILE       = os.path.join(LOGS_DIR, "backup_monitor.log")
MONITOR_SCHEDULE_MINS  = 30             # Backup interval (minutes)
MONITOR_ARCHIVE_KEEP   = 5             # Max number of backup archives to retain

# --- System Surveillance -----------------------------------------------------
SURV_LOG_FILE          = os.path.join(LOGS_DIR, "system_surveillance.log")
SURV_SCHEDULE_SECS     = 60            # Snapshot interval (seconds)
SURV_CPU_ALERT_PCT     = 85.0          # Alert if CPU exceeds this %
SURV_RAM_ALERT_PCT     = 85.0          # Alert if RAM exceeds this %
SURV_DISK_ALERT_PCT    = 90.0          # Alert if any disk partition exceeds this %

# --- Process Logger -----------------------------------------------------------
PROC_LOG_FILE          = os.path.join(LOGS_DIR, "process_logger.log")
PROC_SCHEDULE_SECS     = 30            # Snapshot interval (seconds)
PROC_TOP_N             = 15            # Number of top processes to log per snapshot
PROC_SORT_BY           = "memory"      # "memory" | "cpu" | "pid"
