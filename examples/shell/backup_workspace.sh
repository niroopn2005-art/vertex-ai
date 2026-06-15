#!/usr/bin/env bash
# ==============================================================================
# OpenClaw Backup Automation Script
#
# Description:
#   Safely archives and compresses the OpenClaw configuration directory (~/.openclaw),
#   databases, logs, and workspaces. Features automated rotation to prevent storage exhaustion.
#
# Usage:
#   ./backup_workspace.sh [--backup-dir <path>] [--keep <count>]
# ==============================================================================

set -euo pipefail

# Default configuration
OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
BACKUP_DIR="$OPENCLAW_DIR/backups"
KEEP_COUNT=5

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --backup-dir)
      BACKUP_DIR="$2"
      shift 2
      ;;
    --keep)
      KEEP_COUNT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--backup-dir <path>] [--keep <count>]" >&2
      exit 1
      ;;
  esac
done

echo "============================================="
echo "        OpenClaw Workspace Backup"
echo "============================================="

# 1. Check if OpenClaw directory exists
if [[ ! -d "$OPENCLAW_DIR" ]]; then
  echo "Error: OpenClaw state directory not found at $OPENCLAW_DIR." >&2
  echo "Has the gateway been run or onboarded yet?" >&2
  exit 1
fi

# 2. Prepare backup directory
mkdir -p "$BACKUP_DIR"

# 3. Define backup name
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/openclaw_backup_$TIMESTAMP.tar.gz"

echo "OpenClaw Path: $OPENCLAW_DIR"
echo "Backup Output: $BACKUP_FILE"
echo "Starting backup compression..."

# 4. Perform compression, excluding previous backups and lockfiles
# We exclude the backups folder to prevent nested backups
tar --exclude="$BACKUP_DIR" \
    --exclude="*.sock" \
    --exclude="*.log" \
    -czf "$BACKUP_FILE" -C "$(dirname "$OPENCLAW_DIR")" "$(basename "$OPENCLAW_DIR")"

# Verify backup success
if [[ -f "$BACKUP_FILE" ]]; then
  SIZE_BYTES=$(wc -c < "$BACKUP_FILE")
  SIZE_HUMAN=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "✔ Backup completed successfully!"
  echo "  Archive size: $SIZE_HUMAN ($SIZE_BYTES bytes)"
else
  echo "✘ Error: Failed to write backup archive." >&2
  exit 1
fi

# 5. Rotate old backups (keep only the last N files)
echo "Rotating old archives (keeping last $KEEP_COUNT)..."
cd "$BACKUP_DIR"

# List backup files matching the format, sorted by modification time (oldest first)
# and delete files exceeding the keep limit
# shellcheck disable=SC2012
ls -t openclaw_backup_*.tar.gz 2>/dev/null | tail -n +$((KEEP_COUNT + 1)) | while read -r old_backup; do
  echo "  Removing expired backup: $old_backup"
  rm "$old_backup"
done

echo "Backup rotation complete."
echo "============================================="
