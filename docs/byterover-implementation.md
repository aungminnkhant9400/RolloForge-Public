# ByteRover Memory Plugin Implementation Plan

> **Priority:** 9.5/10 | **Effort:** 30-45 min | **Status:** Ready to implement  
> **Source:** [bookmark_kevinnguyendn_byterover](https://x.com/kevinnguyendn/status/2036457783906934959)

---

## Overview

ByteRover is a **native, structured, long-term memory plugin for OpenClaw** that solves the core memory problem without vector databases. It integrates directly into OpenClaw's Context Engine and prompt assembly flow.

### Key Features
- **>92% retrieval accuracy** using structured Context Tree (zero vector DBs)
- **24/7 Memory Loop** - continuous learning and recall
- **Real-Time Learning** - injects curated knowledge into system prompts
- **Automatic Memory Flush** - extracts insights before hitting token limits
- **Daily Knowledge Mining** - 9 AM cron for architectural decisions
- **Local-by-default** - works offline, team-ready

---

## Architecture

### OpenClaw Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Runtime                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │   Hooks     │───▶│ContextEngine │───▶│  Prompt Assembly │    │
│  │  (Plugin)   │    │  (ByteRover) │    │  (Inject Memory) │    │
│  └─────────────┘    └──────────────┘    └─────────────────┘    │
│         │                   │                                        │
│         ▼                   ▼                                        │
│  ┌─────────────┐    ┌──────────────┐                                │
│  │beforePrompt │    │ Context Tree │                                │
│  │   Build     │    │  (SQLite)    │                                │
│  └─────────────┘    └──────────────┘                                │
│         │                                                          │
│         ▼                                                          │
│  ┌─────────────┐    ┌──────────────┐                                │
│  │afterTurn    │───▶│ Memory Flush │                                │
│  │             │    │  (Extract)   │                                │
│  └─────────────┘    └──────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

### Hook Registration

ByteRover registers with these OpenClaw plugin hooks:

| Hook | Purpose |
|------|---------|
| `beforePromptBuild` | Inject relevant memories into system prompt |
| `afterTurn` | Persist conversation to memory store |
| `beforeCompaction` | Extract key insights before context compaction |
| `sessionStart` | Load user context and preferences |
| `sessionEnd` | Finalize memory writes and flush |

### Context Tree Structure

```typescript
interface ContextNode {
  id: string;
  type: 'fact' | 'preference' | 'decision' | 'action' | 'relation';
  content: string;
  importance: number;      // 0-1 score
  lastAccessed: Date;
  accessCount: number;     // for LRU eviction
  tags: string[];
  source: string;          // session or origin
  createdAt: Date;
}

interface ContextTree {
  roots: ContextNode[];
  index: Map<string, ContextNode>;  // fast lookup
  relations: Map<string, string[]>; // node relationships
}
```

---

## Implementation Steps

### Step 1: Install ByteRover Plugin (5 min)

```bash
# Download and install ByteRover plugin
curl -fsSL https://raw.githubusercontent.com/kevinnguyendn/byterover-openclaw/main/install.sh | bash

# Or manual installation:
git clone https://github.com/kevinnguyendn/byterover-openclaw.git ~/.openclaw/plugins/byterover
cd ~/.openclaw/plugins/byterover && npm install
```

### Step 2: Configure OpenClaw (5 min)

Add to `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "byterover": {
        "enabled": true,
        "path": "~/.openclaw/plugins/byterover",
        "config": {
          "memory": {
            "storage": {
              "type": "sqlite",
              "path": "~/.openclaw/memory/byterover.db"
            },
            "retrieval": {
              "maxMemoriesPerPrompt": 10,
              "minImportanceThreshold": 0.3,
              "contextWindow": 5
            },
            "mining": {
              "enabled": true,
              "cron": "0 9 * * *",
              "extractArchitecturalDecisions": true,
              "extractPreferences": true
            },
            "flush": {
              "enabled": true,
              "triggerTokens": 12000,
              "extractInsightsBeforeCompaction": true
            }
          }
        }
      }
    }
  }
}
```

### Step 3: Enable Plugin (1 min)

```bash
# Restart OpenClaw gateway to load plugin
openclaw gateway restart

# Or use the plugin CLI
openclaw plugin enable byterover
```

### Step 4: Verify Installation (2 min)

```bash
# Check plugin status
openclaw plugin list

# Should show:
# ✓ byterover  [enabled]  v1.0.0  Native memory plugin

# Test memory retrieval
openclaw eval "Remember that my name is Rollo and I like trading automation"

# Verify memory was stored
openclaw memory search "Rollo trading"
```

### Step 5: Migrate Existing Memory (15 min)

See [Migration Path](#migration-path) section below.

---

## Migration Path: Markdown → ByteRover

### Current State Analysis

Your current memory system:
```
~/.openclaw/workspace/memory/
├── 2026-03-17.md
├── 2026-03-20.md
├── 2026-03-25.md
├── 2026-03-28.md
├── 2026-03-29.md
├── 2026-03-31.md
├── RolloForge_WORKFLOW.md
├── bookmark-intelligence-2026-03-31.md
└── weekly-priorities-2026-03-31.md
```

### Migration Strategy

**Option A: Automated Migration (Recommended)**

Run the provided migration script:

```bash
# This script is included in install package
~/.openclaw/plugins/byterover/scripts/migrate-markdown.sh \
  --source ~/.openclaw/workspace/memory \
  --format structured
```

What it does:
1. Parses all markdown files by date
2. Extracts key facts, decisions, and preferences
3. Creates Context Tree nodes with proper tagging
4. Sets importance scores based on recency and mentions
5. Preserves original files as backup

**Option B: Gradual Migration**

Keep markdown for historical reference, let ByteRover learn going forward:

```json
{
  "migration": {
    "mode": "gradual",
    "importHistorical": false,
    "referenceLegacyMemory": true,
    "legacyPath": "~/.openclaw/workspace/memory"
  }
}
```

**Option C: Hybrid (Best of Both)**

```
ByteRover (active memory)
  └── Real-time, high-retrieval, conversation context

Markdown (archival memory)
  └── Daily logs, long-term reference, human-readable
```

Configure ByteRover to reference markdown archives when needed:

```json
{
  "memory": {
    "archives": {
      "enabled": true,
      "paths": ["~/.openclaw/workspace/memory"],
      "searchDepth": "deep",  // search archives when live memory insufficient
      "trigger": "on_miss"    // only search archives when no live matches
    }
  }
}
```

### Migration Script Details

The migration script (`migrate-markdown.sh`) extracts:

| Markdown Element | ByteRover Node Type | Example |
|-----------------|---------------------|---------|
| `## Section Headers` | `decision` or `action` | "## Problems Solved" → decision node |
| `- [x] Checklist items` | `action` | Completed actions with timestamps |
| **Bold key terms** | `fact` | "**API Rate Limit Issue**" → fact node |
| Table rows | `relation` | Links between entities |
| Code blocks | `preference` | Tool configurations |

---

## Configuration Reference

### Full Config Schema

```json
{
  "plugins": {
    "entries": {
      "byterover": {
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
              "extractRelations": true,
              "reportTarget": "telegram:5887247944"
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
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BYTEROVER_DB_PATH` | SQLite database location | `~/.openclaw/memory/byterover.db` |
| `BYTEROVER_MINING_CRON` | Daily mining schedule | `0 9 * * *` |
| `BYTEROVER_MAX_MEMORIES` | Memories per prompt | `10` |
| `BYTEROVER_IMPORTANCE_THRESHOLD` | Minimum importance score | `0.3` |

---

## CLI Commands

Once installed, ByteRover adds these commands:

```bash
# Memory management
openclaw memory search <query>          # Search memories
openclaw memory add <content> --type    # Add manual memory
openclaw memory forget <id>             # Remove specific memory
openclaw memory list --tag <tag>        # List memories by tag
openclaw memory stats                   # Show memory statistics

# Knowledge mining
openclaw memory mine                    # Trigger manual knowledge mining
openclaw memory mine --report           # Mine and send report

# Import/Export
openclaw memory export --format json    # Export all memories
openclaw memory import <file>           # Import memories
```

---

## Testing Checklist

Before considering implementation complete:

- [ ] Plugin loads without errors (`openclaw plugin list`)
- [ ] Basic memory storage works (say "remember X", verify retrieval)
- [ ] Memory injection into prompts works (check system prompt)
- [ ] Automatic memory flush triggers correctly
- [ ] Daily knowledge mining runs (check at 9 AM or trigger manually)
- [ ] Migration script runs without errors
- [ ] Historical memories are searchable
- [ ] Performance: <100ms retrieval time

---

## Troubleshooting

### Plugin Won't Load
```bash
# Check logs
openclaw logs --plugin byterover

# Verify path
ls -la ~/.openclaw/plugins/byterover

# Reinstall
rm -rf ~/.openclaw/plugins/byterover
curl -fsSL https://raw.githubusercontent.com/kevinnguyendn/byterover-openclaw/main/install.sh | bash
```

### Memory Not Being Retrieved
```bash
# Check if memories exist
openclaw memory stats

# Verify importance threshold isn't too high
openclaw config get plugins.entries.byterover.config.memory.retrieval.minImportanceThreshold

# Force a search
openclaw memory search "test" --threshold 0.1
```

### Migration Issues
```bash
# Run migration with debug
DEBUG=1 ~/.openclaw/plugins/byterover/scripts/migrate-markdown.sh --source ~/.openclaw/workspace/memory

# Check for malformed markdown
find ~/.openclaw/workspace/memory -name "*.md" -exec markdownlint {} \;
```

---

## Next Steps After Installation

1. **Monitor for 24 hours** - Verify daily mining works
2. **Tune importance threshold** - Adjust if too much/no memory retrieved
3. **Tag important memories** - Use `openclaw memory tag` for key items
4. **Review weekly mining reports** - Check for missed insights
5. **Archive old markdown** - After 30 days of successful ByteRover use

---

## Resources

- **ByteRover Repo:** https://github.com/kevinnguyendn/byterover-openclaw
- **Original Tweet:** https://x.com/kevinnguyendn/status/2036457783906934959
- **OpenClaw Plugin Docs:** https://docs.openclaw.ai/plugins
- **Context Engine API:** See `~/.npm-global/lib/node_modules/openclaw/dist/plugin-sdk/context-engine/`

---

*Generated for RolloForge | ByteRover Priority 9.5 Item*
