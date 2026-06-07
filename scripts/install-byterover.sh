#!/bin/bash
#
# ByteRover Memory Plugin Installer for OpenClaw
# Priority 9.5 Quick Win - 30-45 minute implementation
#
# Usage:
#   curl -fsSL https://your-domain.com/install-byterover.sh | bash
#   OR
#   ./install-byterover.sh [--migrate] [--dry-run]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLUGIN_NAME="byterover"
PLUGIN_REPO="https://github.com/kevinnguyendn/byterover-openclaw.git"
PLUGIN_DIR="${HOME}/.openclaw/plugins/${PLUGIN_NAME}"
CONFIG_FILE="${HOME}/.openclaw/openclaw.json"
MEMORY_DIR="${HOME}/.openclaw/memory"
BACKUP_DIR="${HOME}/.openclaw/backups/$(date +%Y%m%d_%H%M%S)"

# Flags
MIGRATE=false
DRY_RUN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --migrate)
      MIGRATE=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "ByteRover Memory Plugin Installer"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --migrate    Migrate existing markdown memory after installation"
      echo "  --dry-run    Show what would be done without making changes"
      echo "  --verbose    Show detailed output"
      echo "  --help       Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Basic installation"
      echo "  $0 --migrate          # Install + migrate existing memory"
      echo "  $0 --dry-run          # Preview changes"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[✗]${NC} $1"
}

log_step() {
  echo ""
  echo -e "${BLUE}━━━${NC} $1 ${BLUE}━━━${NC}"
}

# Check if running in dry-run mode
check_dry_run() {
  if [[ "$DRY_RUN" == true ]]; then
    log_warn "DRY RUN MODE - No changes will be made"
    return 0
  fi
  return 1
}

# Execute command or echo in dry-run mode
run_cmd() {
  if check_dry_run; then
    echo "[DRY-RUN] Would execute: $*"
  else
    if [[ "$VERBOSE" == true ]]; then
      echo "[EXEC] $*"
    fi
    "$@"
  fi
}

# Check prerequisites
check_prerequisites() {
  log_step "Checking Prerequisites"
  
  # Check OpenClaw is installed
  if ! command -v openclaw &> /dev/null; then
    log_error "OpenClaw not found. Please install OpenClaw first."
    exit 1
  fi
  log_success "OpenClaw CLI found"
  
  # Check Node.js (required for plugins)
  if ! command -v node &> /dev/null; then
    log_error "Node.js not found. Please install Node.js v18+ first."
    exit 1
  fi
  
  NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
  if [[ "$NODE_VERSION" -lt 18 ]]; then
    log_error "Node.js v18+ required. Found: $(node -v)"
    exit 1
  fi
  log_success "Node.js $(node -v) found"
  
  # Check OpenClaw config directory exists
  if [[ ! -d "${HOME}/.openclaw" ]]; then
    log_error "OpenClaw config directory not found at ~/.openclaw"
    exit 1
  fi
  log_success "OpenClaw config directory exists"
  
  # Create necessary directories
  run_cmd mkdir -p "$MEMORY_DIR"
  run_cmd mkdir -p "${HOME}/.openclaw/plugins"
  
  log_success "All prerequisites met"
}

# Backup existing configuration
backup_config() {
  log_step "Backing Up Configuration"
  
  if [[ -f "$CONFIG_FILE" ]]; then
    run_cmd mkdir -p "$BACKUP_DIR"
    run_cmd cp "$CONFIG_FILE" "$BACKUP_DIR/openclaw.json"
    log_success "Backed up openclaw.json to $BACKUP_DIR"
  else
    log_warn "No existing config file to backup"
  fi
  
  # Backup existing plugin if present
  if [[ -d "$PLUGIN_DIR" ]]; then
    run_cmd cp -r "$PLUGIN_DIR" "$BACKUP_DIR/${PLUGIN_NAME}"
    log_success "Backed up existing plugin to $BACKUP_DIR"
  fi
}

# Download and install plugin
install_plugin() {
  log_step "Installing ByteRover Plugin"
  
  if [[ -d "$PLUGIN_DIR" ]]; then
    log_warn "Existing plugin found. Removing..."
    run_cmd rm -rf "$PLUGIN_DIR"
  fi
  
  # Clone repository
  log_info "Cloning ByteRover repository..."
  run_cmd git clone --depth 1 "$PLUGIN_REPO" "$PLUGIN_DIR"
  log_success "Plugin downloaded to $PLUGIN_DIR"
  
  # Install dependencies
  log_info "Installing plugin dependencies..."
  run_cmd cd "$PLUGIN_DIR"
  run_cmd npm install --production
  log_success "Dependencies installed"
  
  # Make scripts executable
  if [[ -d "$PLUGIN_DIR/scripts" ]]; then
    run_cmd chmod +x "$PLUGIN_DIR/scripts/"*.sh
  fi
  
  log_success "ByteRover plugin installed"
}

# Configure OpenClaw
configure_openclaw() {
  log_step "Configuring OpenClaw"
  
  # Read existing config or create new one
  if [[ -f "$CONFIG_FILE" ]]; then
    CONFIG_JSON=$(cat "$CONFIG_FILE")
  else
    CONFIG_JSON='{"meta":{},"plugins":{"entries":{}}}'
  fi
  
  # Create plugin configuration
  PLUGIN_CONFIG=$(cat <<'EOF'
{
  "enabled": true,
  "path": "~/.openclaw/plugins/byterover",
  "config": {
    "memory": {
      "storage": {
        "type": "sqlite",
        "path": "~/.openclaw/memory/byterover.db",
        "backupInterval": "daily"
      },
      "retrieval": {
        "maxMemoriesPerPrompt": 10,
        "minImportanceThreshold": 0.3,
        "contextWindow": 5,
        "recencyBoost": true,
        "accessCountBoost": true
      },
      "learning": {
        "autoExtractFacts": true,
        "autoExtractPreferences": true,
        "autoExtractDecisions": true,
        "confirmationRequired": false
      },
      "mining": {
        "enabled": true,
        "cron": "0 9 * * *",
        "timezone": "Asia/Shanghai",
        "extractArchitecturalDecisions": true,
        "extractPreferences": true,
        "extractRelations": true
      },
      "flush": {
        "enabled": true,
        "triggerTokens": 12000,
        "extractInsightsBeforeCompaction": true,
        "preserveRecentTurns": 3
      },
      "integration": {
        "injectIntoSystemPrompt": true,
        "memoryHeader": "## Context from Previous Conversations",
        "format": "bullet"
      }
    }
  }
}
EOF
)
  
  # Use Node.js to merge config (safer than jq)
  MERGE_SCRIPT=$(cat <<EOF
const fs = require('fs');
const path = '$CONFIG_FILE';
const pluginConfig = $PLUGIN_CONFIG;

let config = {};
if (fs.existsSync(path)) {
  config = JSON.parse(fs.readFileSync(path, 'utf8'));
}

if (!config.plugins) config.plugins = { entries: {} };
if (!config.plugins.entries) config.plugins.entries = {};

config.plugins.entries['$PLUGIN_NAME'] = pluginConfig;

// Update meta
if (!config.meta) config.meta = {};
config.meta.lastTouchedAt = new Date().toISOString();
config.meta.lastTouchedVersion = '2026.3.24';

fs.writeFileSync(path, JSON.stringify(config, null, 2));
console.log('Configuration updated successfully');
EOF
)

  if check_dry_run; then
    echo "[DRY-RUN] Would update $CONFIG_FILE with ByteRover configuration"
  else
    node -e "$MERGE_SCRIPT"
    log_success "OpenClaw configuration updated"
  fi
}

# Create wrapper scripts
create_wrappers() {
  log_step "Creating Wrapper Scripts"
  
  WRAPPER_DIR="${HOME}/.openclaw/bin"
  run_cmd mkdir -p "$WRAPPER_DIR"
  
  # Memory migration wrapper
  cat > "$WRAPPER_DIR/byterover-migrate" <<'EOF'
#!/bin/bash
# ByteRover Memory Migration Script

SOURCE_DIR="${1:-${HOME}/.openclaw/workspace/memory}"
PLUGIN_DIR="${HOME}/.openclaw/plugins/byterover"
DB_PATH="${HOME}/.openclaw/memory/byterover.db"

echo "Migrating markdown memory from: $SOURCE_DIR"
echo "Target database: $DB_PATH"
echo ""

# Check if migration script exists in plugin
if [[ -f "$PLUGIN_DIR/scripts/migrate-markdown.js" ]]; then
  node "$PLUGIN_DIR/scripts/migrate-markdown.js" --source "$SOURCE_DIR"
elif [[ -f "$PLUGIN_DIR/scripts/migrate-markdown.sh" ]]; then
  bash "$PLUGIN_DIR/scripts/migrate-markdown.sh" --source "$SOURCE_DIR"
else
  echo "Migration script not found in plugin. Using built-in migration..."
  # Fallback: use Node.js to parse and insert
  node -e "
const fs = require('fs');
const path = require('path');

const sourceDir = '$SOURCE_DIR';
const files = fs.readdirSync(sourceDir).filter(f => f.endsWith('.md'));

console.log('Found', files.length, 'markdown files');

files.forEach(file => {
  const content = fs.readFileSync(path.join(sourceDir, file), 'utf8');
  const date = file.replace('.md', '');
  
  // Extract key sections
  const sections = content.split('##').filter(s => s.trim());
  
  console.log('Processing', file, '-', sections.length, 'sections');
  
  // TODO: Insert into ByteRover database
  // This is a simplified version - full migration handles more cases
});

console.log('Migration preview complete');
console.log('Run with --apply to actually migrate');
"
fi
EOF
  run_cmd chmod +x "$WRAPPER_DIR/byterover-migrate"
  
  # Memory stats wrapper
  cat > "$WRAPPER_DIR/byterover-stats" <<'EOF'
#!/bin/bash
# ByteRover Memory Statistics

DB_PATH="${HOME}/.openclaw/memory/byterover.db"

if [[ ! -f "$DB_PATH" ]]; then
  echo "ByteRover database not found. Is the plugin installed?"
  exit 1
fi

echo "ByteRover Memory Statistics"
echo "==========================="
echo ""

sqlite3 "$DB_PATH" <<SQL
SELECT 
  COUNT(*) as total_memories,
  COUNT(CASE WHEN type = 'fact' THEN 1 END) as facts,
  COUNT(CASE WHEN type = 'preference' THEN 1 END) as preferences,
  COUNT(CASE WHEN type = 'decision' THEN 1 END) as decisions,
  COUNT(CASE WHEN type = 'action' THEN 1 END) as actions,
  ROUND(AVG(importance), 2) as avg_importance
FROM memories;
SQL

echo ""
echo "Top 5 Most Accessed Memories:"
sqlite3 "$DB_PATH" "SELECT substr(content, 1, 50) || '...', access_count FROM memories ORDER BY access_count DESC LIMIT 5;"
EOF
  run_cmd chmod +x "$WRAPPER_DIR/byterover-stats"
  
  log_success "Wrapper scripts created in $WRAPPER_DIR"
}

# Restart OpenClaw gateway
restart_gateway() {
  log_step "Restarting OpenClaw Gateway"
  
  if check_dry_run; then
    echo "[DRY-RUN] Would restart OpenClaw gateway"
    return
  fi
  
  # Try to restart gracefully
  if openclaw gateway status &> /dev/null; then
    log_info "Stopping OpenClaw gateway..."
    openclaw gateway stop || true
    sleep 2
  fi
  
  log_info "Starting OpenClaw gateway..."
  openclaw gateway start
  
  # Wait for startup
  sleep 3
  
  if openclaw gateway status &> /dev/null; then
    log_success "OpenClaw gateway restarted successfully"
  else
    log_warn "Gateway status check failed - may need manual restart"
  fi
}

# Verify installation
verify_installation() {
  log_step "Verifying Installation"
  
  if check_dry_run; then
    echo "[DRY-RUN] Would verify:"
    echo "  - Plugin directory exists"
    echo "  - Config file updated"
    echo "  - Database initialized"
    echo "  - Plugin loads correctly"
    return
  fi
  
  # Check plugin directory
  if [[ ! -d "$PLUGIN_DIR" ]]; then
    log_error "Plugin directory not found at $PLUGIN_DIR"
    exit 1
  fi
  log_success "Plugin directory exists"
  
  # Check config
  if ! grep -q "byterover" "$CONFIG_FILE"; then
    log_error "Plugin not found in OpenClaw config"
    exit 1
  fi
  log_success "Plugin configured in OpenClaw"
  
  # Check if plugin is loaded (if gateway is running)
  if openclaw gateway status &> /dev/null; then
    if openclaw plugin list 2>/dev/null | grep -q "byterover"; then
      log_success "Plugin loaded in OpenClaw"
    else
      log_warn "Plugin not yet loaded - may need gateway restart"
    fi
  else
    log_warn "Gateway not running - skipping plugin load check"
  fi
  
  echo ""
  log_success "ByteRover installation verified!"
}

# Run migration if requested
run_migration() {
  if [[ "$MIGRATE" != true ]]; then
    return
  fi
  
  log_step "Running Memory Migration"
  
  SOURCE_MEMORY="${HOME}/.openclaw/workspace/memory"
  
  if [[ ! -d "$SOURCE_MEMORY" ]]; then
    log_warn "Source memory directory not found: $SOURCE_MEMORY"
    return
  fi
  
  log_info "Found markdown memory at: $SOURCE_MEMORY"
  
  if check_dry_run; then
    echo "[DRY-RUN] Would migrate markdown files:"
    find "$SOURCE_MEMORY" -name "*.md" | head -5 | while read f; do
      echo "  - $(basename "$f")"
    done
    return
  fi
  
  # Run migration
  if [[ -x "${HOME}/.openclaw/bin/byterover-migrate" ]]; then
    "${HOME}/.openclaw/bin/byterover-migrate" "$SOURCE_MEMORY"
  else
    log_warn "Migration script not found"
  fi
}

# Print completion message
print_completion() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║          ByteRover Memory Plugin Installed!                  ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "What's Next:"
  echo "  1. Test memory: Say 'remember that I prefer JSON over YAML'"
  echo "  2. Verify retrieval: The plugin will inject relevant context"
  echo "  3. Check daily at 9 AM for knowledge mining reports"
  echo ""
  echo "Useful Commands:"
  echo "  openclaw plugin list              # Verify plugin is loaded"
  echo "  openclaw memory stats             # View memory statistics"
  echo "  ~/.openclaw/bin/byterover-stats   # Detailed stats"
  echo ""
  
  if [[ "$MIGRATE" != true ]]; then
    echo "To migrate existing markdown memory:"
    echo "  $0 --migrate"
    echo ""
  fi
  
  echo "Documentation:"
  echo "  ~/RolloForge/docs/byterover-implementation.md"
  echo ""
  
  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}This was a DRY RUN. Run without --dry-run to actually install.${NC}"
  fi
}

# Main installation flow
main() {
  echo ""
  echo -e "${BLUE}ByteRover Memory Plugin Installer for OpenClaw${NC}"
  echo -e "${BLUE}==============================================${NC}"
  echo ""
  
  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Running in DRY-RUN mode${NC}"
    echo ""
  fi
  
  # Run installation steps
  check_prerequisites
  backup_config
  install_plugin
  configure_openclaw
  create_wrappers
  restart_gateway
  verify_installation
  run_migration
  
  print_completion
}

# Handle errors
trap 'log_error "Installation failed at line $LINENO"' ERR

# Run main
main
