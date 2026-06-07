#!/bin/bash
#
# Setup script for RolloForge Nightly Build System
# Run this once to configure the nightly build workflow
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🌙 RolloForge Nightly Build - Setup"
echo "===================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi
echo "  ✓ Python 3 found"

# Git
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed"
    exit 1
fi
echo "  ✓ Git found"

# GitHub CLI (optional)
if command -v gh &> /dev/null; then
    echo "  ✓ GitHub CLI found (optional, for automatic PR creation)"
else
    echo "  ⚠ GitHub CLI not found (optional, install for PR creation)"
fi

# Check we're in the right directory
if [ ! -f "$PROJECT_ROOT/forge.py" ]; then
    echo "❌ This doesn't look like a RolloForge directory"
    exit 1
fi
echo "  ✓ RolloForge directory verified"
echo ""

# Make scripts executable
echo "🔧 Setting up scripts..."
chmod +x "$SCRIPT_DIR/nightly-build.py"
chmod +x "$SCRIPT_DIR/nightly-cron.sh"
chmod +x "$SCRIPT_DIR/send-morning-report.py"
echo "  ✓ Scripts made executable"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p "$PROJECT_ROOT/.nightly-backups"
mkdir -p "$PROJECT_ROOT/.nightly-logs"
mkdir -p "$PROJECT_ROOT/reports"
echo "  ✓ Backup directory: $PROJECT_ROOT/.nightly-backups"
echo "  ✓ Log directory: $PROJECT_ROOT/.nightly-logs"
echo "  ✓ Report directory: $PROJECT_ROOT/reports"
echo ""

# Create config file if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.nightly-config" ]; then
    echo "⚙️  Creating configuration file..."
    cp "$SCRIPT_DIR/nightly-config.example" "$SCRIPT_DIR/.nightly-config"
    echo "  ✓ Config created: $SCRIPT_DIR/.nightly-config"
    echo ""
    echo "📝 Next steps:"
    echo "   Edit $SCRIPT_DIR/.nightly-config"
    echo "   Add your GitHub token and Telegram credentials"
else
    echo "  ✓ Config already exists: $SCRIPT_DIR/.nightly-config"
fi
echo ""

# Test the build system
echo "🧪 Testing build system (dry run)..."
cd "$PROJECT_ROOT"
if python3 "$SCRIPT_DIR/nightly-build.py" --dry-run > /tmp/nightly-test.log 2>&1; then
    echo "  ✓ Dry run successful"
    echo ""
    echo "   Health check summary:"
    grep "Step 2:" -A 10 /tmp/nightly-test.log | tail -9 | sed 's/^/     /'
else
    echo "  ⚠ Dry run had issues (check /tmp/nightly-test.log)"
fi
echo ""

# Cron setup
echo "⏰ Cron Setup"
echo "-------------"
echo "To schedule the nightly build, add this to your crontab:"
echo ""
echo "    # RolloForge Nightly Build - Run at 2 AM daily"
echo "    0 2 * * * $SCRIPT_DIR/nightly-cron.sh"
echo ""
echo "    # RolloForge Morning Report - Run at 8 AM daily"
echo "    0 8 * * * $SCRIPT_DIR/send-morning-report.py --telegram"
echo ""
echo "To edit your crontab, run: crontab -e"
echo ""

# GitHub authentication check
echo "🔐 GitHub Setup (for automatic PRs)"
echo "-----------------------------------"
if command -v gh &> /dev/null; then
    if gh auth status > /dev/null 2>&1; then
        echo "  ✓ GitHub CLI is authenticated"
    else
        echo "  ⚠ GitHub CLI not authenticated"
        echo "     Run: gh auth login"
    fi
else
    echo "  Install GitHub CLI: https://cli.github.com/"
fi
echo ""

# Summary
echo "===================================="
echo "✅ Setup Complete!"
echo ""
echo "Quick commands:"
echo "  ./scripts/nightly-build.py --dry-run      # Test without changes"
echo "  ./scripts/nightly-build.py                # Full build"
echo "  ./scripts/nightly-build.py --list-backups # View backups"
echo ""
echo "Documentation:"
echo "  $PROJECT_ROOT/docs/NIGHTLY_BUILD.md"
echo ""
echo "Next steps:"
echo "  1. Edit scripts/.nightly-config with your credentials"
echo "  2. Run: ./scripts/nightly-build.py --dry-run"
echo "  3. Add to crontab for automated runs"
echo ""
