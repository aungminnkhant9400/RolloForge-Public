# ByteRover Quick Reference Card

## One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/rolloforge/rollo-forge/main/scripts/install-byterover.sh | bash
```

## One-Line Install + Migrate
```bash
curl -fsSL https://raw.githubusercontent.com/rolloforge/rollo-forge/main/scripts/install-byterover.sh | bash -s -- --migrate
```

## Manual Steps (if preferred)

### 1. Install (5 min)
```bash
cd ~/RolloForge
./scripts/install-byterover.sh
```

### 2. Migrate Memory (optional, 10 min)
```bash
./scripts/migrate-to-byterover.sh --apply
```

### 3. Verify (2 min)
```bash
openclaw plugin list | grep byterover
openclaw memory stats
```

---

## Daily Usage

### Natural Memory
Just tell OpenClaw:
- "Remember that I prefer Python over JavaScript"
- "Note that my trading strategy is momentum-based"
- "Don't forget I'm UTC+8 timezone"

### Search Memory
```bash
openclaw memory search "trading strategy"
openclaw memory search "python preference"
```

### View Stats
```bash
~/.openclaw/bin/byterover-stats
```

---

## Key Features

| Feature | What It Does | When It Runs |
|---------|--------------|--------------|
| **Real-Time Learning** | Injects relevant memories into prompts | Every conversation |
| **Memory Flush** | Extracts insights before token limit | When context > 12k tokens |
| **Daily Mining** | Discovers patterns and decisions | Every day at 9 AM |
| **Context Tree** | Structured storage (no vector DB) | Always |

---

## Configuration

Edit `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "byterover": {
        "enabled": true,
        "config": {
          "memory": {
            "retrieval": {
              "maxMemoriesPerPrompt": 10,
              "minImportanceThreshold": 0.3
            },
            "mining": {
              "cron": "0 9 * * *"
            }
          }
        }
      }
    }
  }
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not loading | `openclaw gateway restart` |
| Memory not retrieved | Lower `minImportanceThreshold` to 0.2 |
| Too much memory | Reduce `maxMemoriesPerPrompt` to 5 |
| Migration failed | Check `~/.openclaw/backups/` for original files |

---

## Migration Strategy Options

1. **Full Migration** (recommended): Move all markdown to ByteRover
2. **Gradual**: Keep markdown archive, let ByteRover learn going forward  
3. **Hybrid**: ByteRover for active memory, markdown for long-term reference

See full guide: `~/RolloForge/docs/byterover-implementation.md`
