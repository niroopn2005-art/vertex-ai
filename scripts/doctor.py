#!/usr/bin/env python3
"""
Vertex AI — Setup & Health Check Utility
Validates your environment, config, and gateway connectivity.
"""

import json
import os
import sys
import subprocess
import socket
import argparse
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_PORT = 18789

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[2m"


def banner():
    print(f"""
{CYAN}{BOLD}
  ██╗   ██╗███████╗██████╗ ████████╗███████╗██╗  ██╗     █████╗ ██╗
  ██║   ██║██╔════╝██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝    ██╔══██╗██║
  ██║   ██║█████╗  ██████╔╝   ██║   █████╗   ╚███╔╝     ███████║██║
  ╚██╗ ██╔╝██╔══╝  ██╔══██╗   ██║   ██╔══╝   ██╔██╗     ██╔══██║██║
   ╚████╔╝ ███████╗██║  ██║   ██║   ███████╗██╔╝ ██╗    ██║  ██║██║
    ╚═══╝  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝
{RESET}
{DIM}  Next-generation AI operating system — Setup & Health Check{RESET}
""")


def check(label: str, ok: bool, detail: str = ""):
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    suffix = f"  {DIM}{detail}{RESET}" if detail else ""
    print(f"  {icon}  {label}{suffix}")
    return ok


def check_node():
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        major = int(version.lstrip("v").split(".")[0])
        ok = major >= 22
        return check("Node.js", ok, f"{version} {'(OK)' if ok else '(need v22+)'}")
    except FileNotFoundError:
        return check("Node.js", False, "not found — install from nodejs.org")


def check_pnpm():
    try:
        result = subprocess.run(["pnpm", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        return check("pnpm", True, f"v{version}")
    except FileNotFoundError:
        return check("pnpm", False, "not found — run: npm install -g pnpm")


def check_config():
    if not CONFIG_PATH.exists():
        return check("Config file", False, f"not found at {CONFIG_PATH}")
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        has_model = bool(
            config.get("agents", {}).get("defaults", {}).get("model")
        )
        has_key = bool(
            config.get("models", {}).get("providers", {})
        )
        check("Config file", True, str(CONFIG_PATH))
        check("Model configured", has_model,
              config.get("agents", {}).get("defaults", {}).get("model", "not set"))
        check("API key present", has_key,
              f"{len(config.get('models', {}).get('providers', {}))} provider(s)")
        return True
    except json.JSONDecodeError as e:
        return check("Config file", False, f"invalid JSON: {e}")


def check_gateway(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        running = result == 0
        return check(
            f"Gateway (port {port})",
            running,
            "running ✓" if running else "not running — start with: pnpm gateway:watch"
        )
    except Exception as e:
        return check(f"Gateway (port {port})", False, str(e))
    finally:
        sock.close()


def check_workspace():
    workspace = Path.home() / ".openclaw" / "workspace"
    exists = workspace.exists()
    if exists:
        files = list(workspace.glob("*.md"))
        return check("Workspace", True, f"{len(files)} markdown file(s) at {workspace}")
    return check("Workspace", False, f"not found at {workspace} — run: pnpm openclaw setup")


def check_python():
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 8)
    return check("Python", ok, f"v{version}")


def run_doctor(port: int):
    banner()
    print(f"{BOLD}Running health checks...{RESET}\n")

    results = []
    results.append(check_python())
    results.append(check_node())
    results.append(check_pnpm())
    results.append(check_config())
    results.append(check_workspace())
    results.append(check_gateway(port))

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print()
    if failed == 0:
        print(f"{GREEN}{BOLD}  All checks passed! Vertex AI is ready.{RESET}")
    else:
        print(f"{YELLOW}{BOLD}  {failed} check(s) failed. Review the items above.{RESET}")

    print(f"  {DIM}Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    return 0 if failed == 0 else 1


def show_config():
    if not CONFIG_PATH.exists():
        print(f"{RED}Config not found at {CONFIG_PATH}{RESET}")
        print(f"Run: pnpm openclaw setup")
        return 1
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # Redact secrets
    if "models" in config and "providers" in config["models"]:
        for provider in config["models"]["providers"].values():
            if "apiKey" in provider:
                key = provider["apiKey"]
                provider["apiKey"] = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
    if "gateway" in config and "auth" in config["gateway"]:
        token = config["gateway"]["auth"].get("token", "")
        if token:
            config["gateway"]["auth"]["token"] = f"{token[:8]}...{token[-4:]}"

    print(f"\n{BOLD}Vertex AI Config{RESET} ({CONFIG_PATH})\n")
    print(json.dumps(config, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Vertex AI — Setup & Health Check Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  doctor      Run all health checks (default)
  config      Show current config (secrets redacted)

Examples:
  python3 scripts/doctor.py
  python3 scripts/doctor.py doctor --port 18789
  python3 scripts/doctor.py config
        """
    )
    parser.add_argument("command", nargs="?", default="doctor",
                        choices=["doctor", "config"],
                        help="Command to run (default: doctor)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Gateway port to check (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    if args.command == "config":
        sys.exit(show_config())
    else:
        sys.exit(run_doctor(args.port))


if __name__ == "__main__":
    main()
