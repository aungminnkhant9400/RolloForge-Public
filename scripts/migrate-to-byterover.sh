#!/bin/bash
#
# ByteRover Markdown Memory Migration Script
# Migrates existing markdown memory files to ByteRover structured storage
#
# Usage:
#   ./migrate-to-byterover.sh [--source PATH] [--dry-run] [--apply]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SOURCE_DIR="${HOME}/.openclaw/workspace/memory"
DB_PATH="${HOME}/.openclaw/memory/byterover.db"
BACKUP_DIR="${HOME}/.openclaw/backups/memory-$(date +%Y%m%d_%H%M%S)"
APPLY=false
DRY_RUN=false
VERBOSE=false

# Statistics
STATS_TOTAL=0
STATS_MIGRATED=0
STATS_SKIPPED=0
STATS_ERRORS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --source)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --apply)
      APPLY=true
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
      echo "ByteRover Markdown Memory Migration"
      echo ""
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --source PATH    Source directory for markdown files"
      echo "                   (default: ~/.openclaw/workspace/memory)"
      echo "  --apply          Actually perform migration (default: preview only)"
      echo "  --dry-run        Show what would be done without changes"
      echo "  --verbose        Show detailed output"
      echo "  --help           Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                              # Preview migration"
      echo "  $0 --apply                      # Execute migration"
      echo "  $0 --source ~/my-memory --apply # Migrate custom directory"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_section() { echo ""; echo -e "${BLUE}▶${NC} $1"; }

# Check prerequisites
check_prerequisites() {
  log_section "Checking Prerequisites"
  
  if [[ ! -d "$SOURCE_DIR" ]]; then
    log_error "Source directory not found: $SOURCE_DIR"
    exit 1
  fi
  log_success "Source directory exists: $SOURCE_DIR"
  
  # Count markdown files
  local count=$(find "$SOURCE_DIR" -name "*.md" -type f | wc -l)
  if [[ $count -eq 0 ]]; then
    log_error "No markdown files found in $SOURCE_DIR"
    exit 1
  fi
  log_success "Found $count markdown files to process"
  
  if [[ "$APPLY" == true && "$DRY_RUN" == false ]]; then
    if [[ ! -f "$DB_PATH" ]]; then
      log_warn "ByteRover database not found at $DB_PATH"
      log_info "Database will be created during migration"
    fi
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp -r "$SOURCE_DIR" "$BACKUP_DIR/"
    log_success "Backup created at $BACKUP_DIR"
  fi
}

# Extract date from filename
extract_date() {
  local filename=$(basename "$1" .md)
  # Try YYYY-MM-DD format
  if [[ $filename =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "$filename"
  else
    echo "unknown"
  fi
}

# Parse markdown content and extract memories
parse_markdown() {
  local file="$1"
  local content=$(cat "$file")
  local date=$(extract_date "$file")
  
  # Use Node.js for robust parsing
  node -e "
const content = \`${content//\`/\\\`}\`;
const date = '$date';
const file = '$file';

const memories = [];

// Split into sections
const sections = content.split(/^## /m).filter(s => s.trim());

sections.forEach((section, idx) => {
  const lines = section.split('\\n');
  const header = lines[0].trim();
  const body = lines.slice(1).join('\\n').trim();
  
  // Extract type from header
  let type = 'fact';
  if (header.match(/problem|issue|error|bug|fail/i)) type = 'decision';
  if (header.match(/solved|fixed|completed|done/i)) type = 'action';
  if (header.match(/prefer|like|want/i)) type = 'preference';
  
  // Extract key facts from lists
  const listItems = body.match(/^[-*] \\[?[ x]?\\]? (.+)$/gm) || [];
  
  listItems.forEach(item => {
    const cleanItem = item.replace(/^[-*] \\[?[ x]?\\]? /, '').trim();
    if (cleanItem.length > 10) {
      memories.push({
        type: type,
        content: cleanItem,
        context: header,
        source: file,
        date: date,
        importance: calculateImportance(cleanItem, body)
      });
    }
  });
  
  // Extract bold text as key facts
  const boldItems = body.match(/\\*\\*([^*]+)\\*\\*/g) || [];
  boldItems.forEach(item => {
    const cleanItem = item.replace(/\\*\\*/g, '').trim();
    if (cleanItem.length > 5 && cleanItem.length < 200) {
      memories.push({
        type: 'fact',
        content: cleanItem,
        context: header,
        source: file,
        date: date,
        importance: 0.7
      });
    }
  });
  
  // If section has substantial content but no lists, create a summary memory
  if (listItems.length === 0 && body.length > 50 && body.length < 1000) {
    memories.push({
      type: type,
      content: body.substring(0, 500).replace(/\\n/g, ' '),
      context: header,
      source: file,
      date: date,
      importance: 0.5
    });
  }
});

function calculateImportance(item, context) {
  let score = 0.5;
  
  // Boost for actionable items
  if (item.match(/(built|created|implemented|fixed|solved)/i)) score += 0.2;
  if (item.match(/(problem|issue|critical|urgent)/i)) score += 0.15;
  if (item.match(/(decision|chose|selected)/i)) score += 0.1;
  
  // Boost for recent items (handled by date in actual implementation)
  
  return Math.min(score, 1.0);
}

console.log(JSON.stringify(memories, null, 2));
" 2>/dev/null || echo "[]"
}

# Process a single file
process_file() {
  local file="$1"
  local filename=$(basename "$file")
  
  ((STATS_TOTAL++))
  
  if [[ "$VERBOSE" == true ]]; then
    log_info "Processing: $filename"
  fi
  
  # Parse markdown
  local memories=$(parse_markdown "$file")
  local count=$(echo "$memories" | node -e "console.log(JSON.parse(require('fs').readFileSync(0, 'utf8')).length)" 2>/dev/null || echo "0")
  
  if [[ $count -eq 0 ]]; then
    ((STATS_SKIPPED++))
    if [[ "$VERBOSE" == true ]]; then
      log_warn "No memories extracted from $filename"
    fi
    return
  fi
  
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY-RUN] Would migrate $count memories from $filename"
    if [[ "$VERBOSE" == true ]]; then
      echo "$memories" | head -50
    fi
    ((STATS_MIGRATED+=$count))
    return
  fi
  
  if [[ "$APPLY" == false ]]; then
    echo "[PREVIEW] $filename: $count memories would be migrated (use --apply to execute)"
    ((STATS_MIGRATED+=$count))
    return
  fi
  
  # Actually insert into database
  echo "$memories" | node -e "
const memories = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const fs = require('fs');

// For now, write to JSONL file for ByteRover to ingest
const outputFile = '${DB_PATH}.migrations.jsonl';
const stream = fs.createWriteStream(outputFile, { flags: 'a' });

memories.forEach(memory => {
  stream.write(JSON.stringify(memory) + '\\n');
});

stream.end();
console.log('Migrated ' + memories.length + ' memories');
"
  
  if [[ $? -eq 0 ]]; then
    ((STATS_MIGRATED+=$count))
    log_success "Migrated $count memories from $filename"
  else
    ((STATS_ERRORS++))
    log_error "Failed to migrate $filename"
  fi
}

# Main migration loop
run_migration() {
  log_section "Starting Migration"
  
  if [[ "$DRY_RUN" == true ]]; then
    log_warn "DRY RUN MODE - No changes will be made"
  elif [[ "$APPLY" == false ]]; then
    log_warn "PREVIEW MODE - Use --apply to execute migration"
  fi
  
  # Find and process all markdown files
  local files=$(find "$SOURCE_DIR" -name "*.md" -type f | sort)
  
  for file in $files; do
    process_file "$file"
  done
  
  # Finalize if applying
  if [[ "$APPLY" == true && "$DRY_RUN" == false ]]; then
    finalize_migration
  fi
}

# Finalize migration - insert into ByteRover
finalize_migration() {
  log_section "Finalizing Migration"
  
  local jsonl_file="${DB_PATH}.migrations.jsonl"
  
  if [[ ! -f "$jsonl_file" ]]; then
    log_warn "No migration data file found"
    return
  fi
  
  local total_lines=$(wc -l < "$jsonl_file")
  log_info "Found $total_lines memory entries to finalize"
  
  # Call ByteRover import function if available
  if [[ -f "${HOME}/.openclaw/plugins/byterover/scripts/import.js" ]]; then
    node "${HOME}/.openclaw/plugins/byterover/scripts/import.js" "$jsonl_file"
    log_success "Imported into ByteRover"
  else
    log_info "Migration data saved to: $jsonl_file"
    log_info "ByteRover will ingest this on next startup"
  fi
  
  # Create marker file
  echo "$(date -Iseconds) - Migrated $STATS_MIGRATED memories" > "$SOURCE_DIR/.MIGRATED"
}

# Print summary
print_summary() {
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}        Migration Summary${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "Files processed:  $STATS_TOTAL"
  echo "Memories found:   $STATS_MIGRATED"
  echo "Files skipped:    $STATS_SKIPPED"
  echo "Errors:           $STATS_ERRORS"
  echo ""
  
  if [[ $STATS_MIGRATED -gt 0 ]]; then
    if [[ "$APPLY" == true && "$DRY_RUN" == false ]]; then
      log_success "Migration completed successfully!"
      echo ""
      echo "Next steps:"
      echo "  1. Restart OpenClaw gateway if running"
      echo "  2. Test with: openclaw memory search 'your topic'"
      echo "  3. Original files backed up to: $BACKUP_DIR"
    else
      echo "To execute this migration, run:"
      echo "  $0 --apply"
    fi
  fi
  echo ""
}

# Main
main() {
  check_prerequisites
  run_migration
  print_summary
}

main
