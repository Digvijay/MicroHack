"""Command line for the Caldova regulatory intelligence tools.

Run from the lab folder:  python3 -m regintel --help
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import crawler
from .lake import KNOWLEDGE, RAW, Lake, LakeError

DEFAULT_LAKE = crawler.LAB / "out" / "lake"


def _az(*arguments: str) -> None:
    executable = shutil.which("az")
    if not executable:
        raise LakeError("Azure CLI (az) was not found. Use Azure Cloud Shell, Codespaces or the lab devcontainer.")
    command = [executable, *arguments, "--auth-mode", "login", "--only-show-errors", "--output", "none"]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise LakeError(f"Azure Storage command failed: az {' '.join(arguments[:3])}\n{detail}\n"
                        "Check that you are signed in (az login) to the lab subscription and that the storage account name is correct.")


def download(lake: Lake, account: str) -> None:
    """Fetch shared state so a new Cloud Shell session continues where the last one stopped."""
    for prefix in ("state/*", "tracking/*"):
        lake.raw.mkdir(parents=True, exist_ok=True)
        _az("storage", "blob", "download-batch", "--account-name", account, "--source", RAW,
            "--destination", str(lake.raw), "--pattern", prefix, "--overwrite", "true")


def upload(lake: Lake, account: str) -> None:
    for container, folder in ((RAW, lake.raw), (KNOWLEDGE, lake.knowledge)):
        _az("storage", "blob", "upload-batch", "--account-name", account, "--destination", container,
            "--source", str(folder), "--overwrite", "true")
    print(f"Uploaded the lake to storage account '{account}': containers '{RAW}' and '{KNOWLEDGE}'.")


def _print_monitor(report: dict, lake: Lake) -> None:
    print(f"Regulatory Web and Change Monitor - {report['day']} ({report['date']})")
    print(f"  Pages crawled:          {report['pages_crawled']} ({report['navigation_pages']} index pages)")
    print(f"  Links not followed:     {report['skipped_links']} (outside the allowlisted portals)")
    print(f"  New documents:          {len(report['new'])}  {', '.join(report['new'])}")
    print(f"  Updated documents:      {len(report['updated'])}  {', '.join(report['updated'])}")
    print(f"  Duplicates ignored:     {len(report['duplicates'])}")
    for duplicate in report["duplicates"]:
        print(f"    - {duplicate}")
    print(f"  Change events written:  {len(report['new']) + len(report['updated'])}  ({lake.raw / 'events'})")
    print(f"  Change log:             {lake.knowledge / 'change-log.md'}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m regintel", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lake", type=Path, default=DEFAULT_LAKE, help="Local lake folder (default: out/lake)")
    parser.add_argument("--account", help="Storage account name from your lab dashboard. Omit to work locally only.")
    commands = parser.add_subparsers(dest="command", required=True)
    monitor = commands.add_parser("monitor", help="Crawl the portals, detect changes and load the lake")
    monitor.add_argument("--day", required=True, choices=sorted(crawler.DAYS))
    signoff = commands.add_parser("signoff", help="Record a human decision on an action plan")
    signoff.add_argument("file", type=Path, help="JSON sign-off produced in Challenge 5")
    task = commands.add_parser("task", help="Update the status of a task")
    task.add_argument("task_id")
    task.add_argument("--status", required=True, choices=["open", "in progress", "blocked", "done"])
    task.add_argument("--by", required=True, help="Role or person who changed the status")
    task.add_argument("--note", default="")
    commands.add_parser("status", help="Show the change log and task register summary")
    args = parser.parse_args(argv)
    lake = Lake(args.lake)
    try:
        if args.account and args.command != "status":
            download(lake, args.account)
        if args.command == "monitor":
            _print_monitor(lake.monitor(args.day), lake)
        elif args.command == "signoff":
            created = lake.signoff(args.file)
            print("Decision recorded in the audit trail." + (f" Tasks created: {', '.join(created)}" if created else ""))
        elif args.command == "task":
            updated = lake.update_task(args.task_id, args.status, args.by, args.note)
            print(f"{updated['id']} is now '{updated['status']}'.")
        else:
            state = lake.state()
            versions = sum(len(entry["versions"]) for entry in state["documents"].values())
            print(f"Documents: {len(state['documents'])}, versions: {versions}, monitor runs: {len(state['runs'])}")
            tasks = lake.tasks()["tasks"]
            at_risk = [t["id"] for t in tasks if t["status"] != "done" and t["due"] < lake.as_of()]
            print(json.dumps({"tasks": len(tasks), "at_risk": at_risk, "as_of": lake.as_of()}, indent=2))
        if args.account and args.command != "status":
            upload(lake, args.account)
    except LakeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
