#!/usr/bin/env bash
# ==============================================================================
# OpenClaw Development Environment Bootstrap Script
#
# Description:
#   Automates setting up the workspace for local development. Verifies Node.js,
#   Bun, and pnpm installations, configures local environment files, and runs installs.
# ==============================================================================

set -euo pipefail

# Required versions
MIN_NODE_VER="22.19.0"

echo "============================================="
echo "      OpenClaw Dev Environment Setup"
echo "============================================="

# Helper to compare versions
version_ge() {
  printf '%s\n%s' "$2" "$1" | sort -C -V
}

# 1. Verify Node.js presence and version
if ! command -v node &> /dev/null; then
  echo "✘ Error: Node.js is not installed." >&2
  echo "  Please install Node.js $MIN_NODE_VER or newer." >&2
  exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//')
if version_ge "$NODE_VERSION" "$MIN_NODE_VER"; then
  echo "✔ Node.js version: v$NODE_VERSION (matches requirements)"
else
  echo "⚠ Warning: Node.js version v$NODE_VERSION is older than recommended v$MIN_NODE_VER." >&2
  echo "  We recommend upgrading to ensure full compatibility." >&2
fi

# 2. Check Package Managers (pnpm preferred)
if ! command -v pnpm &> /dev/null; then
  echo "pnpm is missing. Attempting to enable Corepack..."
  if command -v corepack &> /dev/null; then
    corepack enable
    echo "✔ Corepack enabled. Standing by..."
  else
    echo "✘ Error: pnpm is required for workspace packages." >&2
    echo "  Please install it globally: npm install -g pnpm" >&2
    exit 1
  fi
else
  echo "✔ pnpm package manager found: v$(pnpm -v)"
fi

# 3. Check for Bun (optional but recommended for test runs)
if command -v bun &> /dev/null; then
  echo "✔ Bun runtime found: v$(bun -v)"
else
  echo "ℹ Info: Bun not found. Standard tests can run under Vitest/Node."
fi

# 4. Copy Environment Template
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f ".env" ]]; then
  echo "Creating .env from .env.example..."
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "✔ Created .env file. Please customize API keys and tokens in .env."
  else
    echo "⚠ Warning: .env.example template not found. Skipping." >&2
  fi
else
  echo "✔ .env file already exists."
fi

# 5. Install Dependencies
echo "Installing monorepo dependencies..."
pnpm install --frozen-lockfile

# 6. Verify Build Target
echo "Compiling monorepo sources..."
pnpm build

echo "============================================="
echo "🎉 OpenClaw development environment is ready!"
echo "To start the gateway in debug watch mode, run:"
echo "  pnpm gateway:watch"
echo "To build and run the Control UI locally, run:"
echo "  pnpm ui:dev"
echo "============================================="
