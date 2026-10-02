"""
main.py -- Python Automation Suite  |  Command-Line Launcher
============================================================
Usage examples
--------------
  python main.py all                     # Run all four tools concurrently
  python main.py cleaner                 # Duplicate-file cleaner only
  python main.py backup                  # Backup & monitor only
  python main.py surveillance            # System surveillance only
  python main.py process                 # Process logger only
  python main.py cleaner backup          # Any combination
  python main.py --once cleaner          # Single run, no schedule loop
  python main.py --interval 10 process   # Override interval (seconds for process/surv)
  python main.py status                  # Print current log sizes & latest timestamps
  python main.py --help                  # Show this help
"""

import sys
import os
import argparse
import threading
import time
import platform as _platform
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

import config
from utils import section

# --- Banner -------------------------------------------------------------------

BANNER = r"""
  ____  _  _   _              _       ____        _ _
 |  _ \| || | | |_ ___  ___  | |     / ___| _   _(_) |_ ___
 | |_) | || |_| __/ _ \/ __| | |    \___ \| | | | | __/ _ \
 |  __/|__   _| ||  __/\__ \ | |___  ___) | |_| | | ||  __/
 |_|      |_|  \__\___||___/ |_____||____/ \__,_|_|\__\___|

      Python Automation Suite  *  v1.0
      File Cleaner  |  Backup Monitor  |  Surveillance  |  Process Logger
"""

TOOL_MAP = {
    "cleaner":     ("File Cleaner",       "file_cleaner",       "start_scheduled"),
    "backup":      ("Backup Monitor",     "backup_monitor",     "start_scheduled"),
    "surveillance":("System Surveillance","system_surveillance","start_scheduled"),
    "process":     ("Process Logger",     "process_logger",     "start_scheduled"),
}


# --- Status Command ----------------------------------------------------------

def _file_status(path: str) -> str:
    if not os.path.exists(path):
        return "not created yet"
    size = os.path.getsize(path)
    mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    kb = size / 1024
    return f"{kb:,.1f} KB  (last written: {mtime})"


def show_status() -> None:
    print(section("LOG FILE STATUS"))
    logs = {
        "Cleaner log":      config.CLEANER_LOG_FILE,
        "Backup/Monitor log": config.MONITOR_LOG_FILE,
        "Surveillance log": config.SURV_LOG_FILE,
        "Process log":      config.PROC_LOG_FILE,
    }
    for name, path in logs.items():
        colour = Fore.GREEN if os.path.exists(path) else Fore.YELLOW
        print(f"  {colour}{name:<22}{Style.RESET_ALL}  {_file_status(path)}")

    # Backup archives
    print(f"\n  {'Backup archives':<22}  ", end="")
    archives = [f for f in os.listdir(config.BACKUP_DIR) if f.endswith(".zip")] \
               if os.path.isdir(config.BACKUP_DIR) else []
    print(f"{len(archives)} archive(s) in {config.BACKUP_DIR}")
    print()


# --- Single-Run Mode ---------------------------------------------------------

def run_once(tool_keys: list[str]) -> None:
    """Import and run each tool's main job function exactly once."""
    for key in tool_keys:
        name, module_name, _ = TOOL_MAP[key]
        print(f"\n{Fore.CYAN}>>  Running {name} ...{Style.RESET_ALL}")
        mod = __import__(module_name)
        # Call run_* function (not the scheduler)
        run_fn_name = f"run_{module_name.replace('_', '_')}"
        # Derive the run function name correctly
        run_fns = {
            "cleaner":      "run_cleaner",
            "backup":       "run_backup_monitor",
            "surveillance": "run_surveillance",
            "process":      "run_process_logger",
        }
        fn = getattr(mod, run_fns[key])
        fn()
        print(f"{Fore.GREEN}[OK]  {name} complete.{Style.RESET_ALL}")


# --- Scheduled / Threaded Mode -----------------------------------------------

def _launch_thread(key: str, interval: int | None) -> threading.Thread:
    name, module_name, start_fn_name = TOOL_MAP[key]
    mod  = __import__(module_name)
    fn   = getattr(mod, start_fn_name)

    def _target():
        try:
            if interval is not None:
                fn(interval)
            else:
                fn()
        except KeyboardInterrupt:
            pass

    t = threading.Thread(target=_target, name=name, daemon=True)
    return t


def run_all_threaded(tool_keys: list[str], interval: int | None) -> None:
    threads = []
    for key in tool_keys:
        t = _launch_thread(key, interval)
        t.start()
        threads.append(t)
        print(f"{Fore.GREEN}  >>  {TOOL_MAP[key][0]} started  (thread: {t.name}){Style.RESET_ALL}")

    print(f"\n{Fore.YELLOW}  All tools running. Press Ctrl+C to stop.{Style.RESET_ALL}\n")
    try:
        while True:
            alive = [t for t in threads if t.is_alive()]
            if not alive:
                break
            time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}  Interrupted -- shutting down ...{Style.RESET_ALL}")


# --- CLI Parser ---------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Python Automation Suite -- run one or more automation tools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "tools",
        nargs="+",
        choices=list(TOOL_MAP.keys()) + ["all", "status"],
        metavar="TOOL",
        help=(
            "Tool(s) to run: "
            "cleaner | backup | surveillance | process | all | status"
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run each tool once and exit (no scheduling loop).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Override the schedule interval. "
            "For cleaner/backup: minutes. For surveillance/process: seconds."
        ),
    )
    return parser


# --- Entry Point --------------------------------------------------------------

def main() -> None:
    # Print banner
    print(Fore.CYAN + BANNER + Style.RESET_ALL)
    print(f"  Platform : {_platform.system()} {_platform.release()}")
    print(f"  Time     : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print(f"  Logs dir : {config.LOGS_DIR}")
    print()

    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # -- status command --------------------------------------------------------
    if "status" in args.tools:
        show_status()
        return

    # -- resolve "all" ----------------------------------------------------------
    tool_keys = list(TOOL_MAP.keys()) if "all" in args.tools else args.tools

    print(section(f"Launching: {', '.join(TOOL_MAP[k][0] for k in tool_keys)}"))
    print()

    if args.once:
        run_once(tool_keys)
    else:
        run_all_threaded(tool_keys, args.interval)


if __name__ == "__main__":
    main()
