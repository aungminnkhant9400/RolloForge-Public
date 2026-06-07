# Multi-Agent Role Manager

A registry system to manage multiple OpenClaw agents with distinct roles, personalities, and permissions — based on Claire Vo's "Sam/Finn/Howie" model.

## Overview

The Agent Manager provides:

- **Agent Registry** with unique IDs
- **Role Definitions** (admin, researcher, executor, creative, analyst, guardian)
- **Permission Scoping** (which channels, which tools)
- **"Soul" Template System** (personality + instructions)
- **Heartbeat Scheduler** per agent (different cadences)
- **CLI Integration** (`forge agent create`, `forge agent list`, `forge agent start`)

## Files Created

| File | Description |
|------|-------------|
| `rolloforge/agent_roles.py` | Role definitions, soul templates, permissions |
| `rolloforge/agent_manager.py` | Core registry and agent management |
| `templates/agent_soul.md.j2` | Jinja2 template for SOUL.md generation |
| `scripts/create_agent.py` | Standalone CLI tool for agent creation |
| `data/agent_registry.json` | Registry storage |

## Roles

### Admin (Sam)
- **Emoji:** 👑
- **Mission:** Coordinate other agents, make high-level decisions
- **Permissions:** Full access
- **Heartbeat:** Every 60 minutes

### Researcher (Finn)
- **Emoji:** 🔍
- **Mission:** Find information, validate sources
- **Permissions:** No command execution (research only)
- **Heartbeat:** Every 120 minutes

### Executor (Howie)
- **Emoji:** ⚡
- **Mission:** Execute tasks, ship code, get shit done
- **Permissions:** Full tool access
- **Heartbeat:** Every 30 minutes

### Creative
- **Emoji:** 🎨
- **Mission:** Generate content, design solutions
- **Permissions:** No command execution
- **Heartbeat:** Every 240 minutes

### Analyst
- **Emoji:** 📊
- **Mission:** Analyze data, identify patterns
- **Permissions:** No command execution
- **Heartbeat:** Every 180 minutes

### Guardian
- **Emoji:** 🛡️
- **Mission:** Review work, identify risks
- **Permissions:** Read-only + warnings
- **Heartbeat:** Every 360 minutes

## CLI Usage

### Create an Agent

```bash
# Basic executor agent
forge agent create "Deploy Bot" --role executor

# Researcher with restrictions
forge agent create "Deep Diver" --role researcher --emoji 🔍 --no-execute

# Guardian for security review
forge agent create "Code Guardian" --role guardian --emoji 🛡️ --no-execute --tags "security"

# With custom emoji and tags
forge agent create "My Bot" --role admin --emoji 👑 --tags "primary,automation"

# Generate SOUL.md immediately
forge agent create "Content Bot" --role creative --generate-soul
```

### List Agents

```bash
# Show active agents
forge agent list

# Show all (including inactive)
forge agent list --all

# Filter by role
forge agent list --role executor
```

### Show Agent Details

```bash
forge agent show <agent-id>
# or by name
forge agent show "Deploy Bot"
```

### Start/Stop Agents

```bash
# Start an agent (generates SOUL.md)
forge agent start <agent-id>

# Start with SOUL generation
forge agent start <agent-id> --generate-soul

# Stop/deactivate
forge agent stop <agent-id>
```

### Generate SOUL.md

```bash
# Print to stdout
forge agent soul <agent-id>

# Save to file
forge agent soul <agent-id> --output /path/to/SOUL.md
```

### Delete Agents

```bash
# Soft delete (deactivate)
forge agent stop <agent-id>

# Hard delete (with confirmation)
forge agent delete <agent-id> --force
```

## Programmatic Usage

```python
from rolloforge.agent_roles import AgentRole
from rolloforge.agent_manager import get_registry

# Get registry
registry = get_registry()

# Create an agent
agent = registry.create(
    name="Code Reviewer",
    role=AgentRole.GUARDIAN,
    emoji="🛡️",
    tags=["security", "review"],
    custom_permissions={
        "can_execute_commands": False,
        "can_send_messages": True,  # Can warn about issues
    }
)

# List agents
agents = registry.list(role=AgentRole.EXECUTOR)

# Get agent
agent = registry.get("agent_id_here")

# Update agent
registry.update("agent_id_here", tags=["updated", "tags"])

# Deactivate
registry.deactivate("agent_id_here")

# Delete
registry.delete("agent_id_here")

# Generate SOUL.md content
soul_content = registry.generate_soul_md("agent_id_here")
```

## Agent Data Structure

```json
{
  "id": "deploy_bot_a1b2c3d4",
  "soul": {
    "name": "Deploy Bot",
    "role": "executor",
    "emoji": "⚡",
    "personality_traits": ["action-oriented", "reliable", "efficient"],
    "voice_description": "Direct, no-nonsense, focused",
    "tone": "direct and efficient",
    "mission": "Execute tasks, implement solutions, and ship code",
    "principles": ["Done is better than perfect", "Ship early, ship often"],
    "expertise": ["coding", "automation", "deployment"],
    "preferred_tools": ["exec", "edit", "write", "read"]
  },
  "permissions": {
    "can_read_files": true,
    "can_write_files": true,
    "can_execute_commands": true,
    "can_use_browser": true,
    "can_send_messages": true,
    "can_access_memory": true
  },
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 30,
    "prompt": "Check for pending tasks and execute them"
  },
  "created_at": "2026-04-02T10:00:00+00:00",
  "is_active": true,
  "total_tasks_completed": 0
}
```

## SOUL.md Template

The generated SOUL.md includes:

- Identity (name, role, emoji, ID)
- Mission statement
- Voice & tone description
- Core principles
- Areas of expertise
- Preferred tools
- Permission matrix
- Heartbeat configuration
- Stats and metadata

## Integration with OpenClaw

The Agent Manager is designed to work with OpenClaw's multi-agent system. When OpenClaw supports spawning agents:

```bash
# Future usage:
openclaw agent spawn --soul agents/deploy_bot_a1b2c3d4/SOUL.md --heartbeat 30
```

For now, the `forge agent start` command prepares the agent by generating the SOUL.md file and activating the agent in the registry.

## Testing

Run the standalone CLI:

```bash
# Show available roles
python scripts/create_agent.py --list-roles

# Show examples
python scripts/create_agent.py --example

# Create agent
python scripts/create_agent.py "My Bot" --role executor --emoji ⚡
```

## Architecture

The Agent Manager follows RolloForge patterns:

- **Dataclasses** for type-safe models (`Agent`, `AgentSoul`, `AgentPermissions`, `HeartbeatConfig`)
- **JSON persistence** in `data/agent_registry.json`
- **CLI integration** via `forge.py` subcommands
- **Jinja2 templates** for SOUL.md generation
- **Role-based defaults** with customization support

## Future Enhancements

- [ ] Agent-to-agent communication protocol
- [ ] Task queue per agent
- [ ] Agent activity logging
- [ ] Web UI for agent management
- [ ] Agent performance metrics
- [ ] Auto-scaling agent pools
