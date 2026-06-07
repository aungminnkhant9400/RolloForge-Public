from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rolloforge.agent_roles import (
    Agent,
    AgentRole,
    AgentSoul,
    AgentPermissions,
    HeartbeatConfig,
    get_role_template,
    get_default_permissions,
    get_default_heartbeat,
)
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for managing agents.
    
    Provides CRUD operations for agents and persists to JSON storage.
    """
    
    def __init__(self, registry_path: Path | str | None = None):
        """
        Initialize the registry.
        
        Args:
            registry_path: Path to the registry JSON file. Defaults to DATA_DIR/agent_registry.json
        """
        if registry_path is None:
            registry_path = DATA_DIR / "agent_registry.json"
        self.registry_path = Path(registry_path)
        self._agents: dict[str, Agent] = {}
        self._load()
    
    def _load(self) -> None:
        """Load agents from storage."""
        if not self.registry_path.exists():
            logger.info(f"Registry file not found at {self.registry_path}, creating new registry")
            self._agents = {}
            return
        
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            self._agents = {
                agent_id: Agent.from_dict(agent_data)
                for agent_id, agent_data in data.get("agents", {}).items()
            }
            logger.info(f"Loaded {len(self._agents)} agents from registry")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to load registry: {e}")
            self._agents = {}
    
    def _save(self) -> None:
        """Save agents to storage."""
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agents": {
                agent_id: agent.to_dict()
                for agent_id, agent in self._agents.items()
            },
        }
        
        # Ensure directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with pretty formatting
        self.registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.debug(f"Saved {len(self._agents)} agents to registry")
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    def create(
        self,
        name: str,
        role: AgentRole | str,
        emoji: str | None = None,
        created_by: str = "system",
        custom_permissions: dict[str, Any] | None = None,
        custom_heartbeat: dict[str, Any] | None = None,
        personality_override: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> Agent:
        """
        Create a new agent.
        
        Args:
            name: The agent's name
            role: The agent's role (use AgentRole enum or string)
            emoji: Custom emoji (defaults to role template)
            created_by: Who created this agent
            custom_permissions: Override default permissions
            custom_heartbeat: Override default heartbeat config
            personality_override: Override soul template values
            tags: Optional tags for the agent
            notes: Optional notes
        
        Returns:
            The created Agent instance
        """
        # Normalize role
        if isinstance(role, str):
            role = AgentRole(role.lower())
        
        # Generate unique ID
        agent_id = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        
        # Get role template
        template = get_role_template(role)
        
        # Build soul from template + overrides
        soul_data = {
            "name": name,
            "role": role.value,
            "emoji": emoji or template.get("emoji", "🤖"),
            **template,
        }
        if personality_override:
            soul_data.update(personality_override)
        
        soul = AgentSoul.from_dict(soul_data)
        
        # Build permissions from defaults + custom
        permissions = get_default_permissions(role)
        if custom_permissions:
            for key, value in custom_permissions.items():
                if hasattr(permissions, key):
                    setattr(permissions, key, value)
        
        # Build heartbeat from defaults + custom
        heartbeat = get_default_heartbeat(role)
        if custom_heartbeat:
            for key, value in custom_heartbeat.items():
                if hasattr(heartbeat, key):
                    setattr(heartbeat, key, value)
        
        now = datetime.now(timezone.utc).isoformat()
        
        agent = Agent(
            id=agent_id,
            soul=soul,
            permissions=permissions,
            heartbeat=heartbeat,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            tags=tags or [],
            notes=notes,
        )
        
        self._agents[agent_id] = agent
        self._save()
        
        logger.info(f"Created agent: {agent_id} ({name} - {role.value})")
        return agent
    
    def get(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def get_by_name(self, name: str) -> Agent | None:
        """Find an agent by name (case-insensitive)."""
        name_lower = name.lower()
        for agent in self._agents.values():
            if agent.soul.name.lower() == name_lower:
                return agent
        return None
    
    def list(
        self,
        role: AgentRole | str | None = None,
        active_only: bool = True,
        tags: list[str] | None = None,
    ) -> list[Agent]:
        """
        List agents with optional filtering.
        
        Args:
            role: Filter by role
            active_only: Only return active agents
            tags: Filter by tags (all must match)
        
        Returns:
            List of matching agents
        """
        results = []
        
        if isinstance(role, str):
            role = AgentRole(role.lower())
        
        for agent in self._agents.values():
            # Filter by active status
            if active_only and not agent.is_active:
                continue
            
            # Filter by role
            if role and agent.soul.role != role:
                continue
            
            # Filter by tags
            if tags:
                if not all(tag in agent.tags for tag in tags):
                    continue
            
            results.append(agent)
        
        # Sort by creation date (newest first)
        results.sort(key=lambda a: a.created_at, reverse=True)
        return results
    
    def update(self, agent_id: str, **updates: Any) -> Agent | None:
        """
        Update an agent's properties.
        
        Args:
            agent_id: The agent's ID
            **updates: Key-value pairs to update
        
        Returns:
            The updated Agent or None if not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        # Handle nested updates
        if "soul" in updates:
            soul_data = agent.soul.to_dict()
            soul_data.update(updates.pop("soul"))
            agent.soul = AgentSoul.from_dict(soul_data)
        
        if "permissions" in updates:
            perm_data = agent.permissions.to_dict()
            perm_data.update(updates.pop("permissions"))
            agent.permissions = AgentPermissions.from_dict(perm_data)
        
        if "heartbeat" in updates:
            hb_data = agent.heartbeat.to_dict()
            hb_data.update(updates.pop("heartbeat"))
            agent.heartbeat = HeartbeatConfig.from_dict(hb_data)
        
        # Handle direct attribute updates
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        agent.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        
        logger.info(f"Updated agent: {agent_id}")
        return agent
    
    def delete(self, agent_id: str) -> bool:
        """
        Delete an agent from the registry.
        
        Args:
            agent_id: The agent's ID
        
        Returns:
            True if deleted, False if not found
        """
        if agent_id not in self._agents:
            return False
        
        del self._agents[agent_id]
        self._save()
        
        logger.info(f"Deleted agent: {agent_id}")
        return True
    
    def deactivate(self, agent_id: str) -> bool:
        """Deactivate an agent (soft delete)."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.is_active = False
        agent.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        
        logger.info(f"Deactivated agent: {agent_id}")
        return True
    
    def activate(self, agent_id: str) -> bool:
        """Activate a deactivated agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.is_active = True
        agent.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        
        logger.info(f"Activated agent: {agent_id}")
        return True
    
    # ========================================================================
    # Stats & Reporting
    # ========================================================================
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total = len(self._agents)
        active = sum(1 for a in self._agents.values() if a.is_active)
        inactive = total - active
        
        by_role: dict[str, int] = {}
        for agent in self._agents.values():
            role = agent.soul.role.value
            by_role[role] = by_role.get(role, 0) + 1
        
        return {
            "total_agents": total,
            "active_agents": active,
            "inactive_agents": inactive,
            "by_role": by_role,
        }
    
    def record_heartbeat(self, agent_id: str) -> bool:
        """Record a heartbeat for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
        self._save()
        return True
    
    def record_task_completion(self, agent_id: str) -> bool:
        """Record a completed task for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.total_tasks_completed += 1
        self._save()
        return True
    
    # ========================================================================
    # Soul Template Generation
    # ========================================================================
    
    def generate_soul_md(self, agent_id: str) -> str | None:
        """
        Generate a SOUL.md content for an agent.
        
        Args:
            agent_id: The agent's ID
        
        Returns:
            Markdown content or None if agent not found
        """
        from jinja2 import Template
        
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        # Load template
        template_path = Path(__file__).parents[1] / "templates" / "agent_soul.md.j2"
        if not template_path.exists():
            # Fallback template
            template_content = self._get_default_soul_template()
        else:
            template_content = template_path.read_text(encoding="utf-8")
        
        template = Template(template_content)
        
        return template.render(
            agent=agent,
            soul=agent.soul,
            permissions=agent.permissions,
            heartbeat=agent.heartbeat,
        )
    
    def _get_default_soul_template(self) -> str:
        """Get the default soul template as fallback."""
        return '''# {{ soul.name }} - Agent Soul

## Identity

- **Name:** {{ soul.name }}
- **Role:** {{ soul.role.value }}
- **Emoji:** {{ soul.emoji }}
- **ID:** {{ agent.id }}

## Mission

{{ soul.mission }}

## Personality

{{ soul.voice_description }}

**Tone:** {{ soul.tone }}

**Traits:**
{% for trait in soul.personality_traits %}- {{ trait }}
{% endfor %}

## Principles

{% for principle in soul.principles %}- {{ principle }}
{% endfor %}

## Expertise

{% for area in soul.expertise %}- {{ area }}
{% endfor %}

## Tools I Use

{% for tool in soul.preferred_tools %}- `{{ tool }}`
{% endfor %}

## Permissions

{% if permissions.can_read_files %}- ✅ Read files{% else %}- ❌ Read files{% endif %}
{% if permissions.can_write_files %}- ✅ Write files{% else %}- ❌ Write files{% endif %}
{% if permissions.can_execute_commands %}- ✅ Execute commands{% else %}- ❌ Execute commands{% endif %}
{% if permissions.can_use_browser %}- ✅ Use browser{% else %}- ❌ Use browser{% endif %}
{% if permissions.can_send_messages %}- ✅ Send messages{% else %}- ❌ Send messages{% endif %}
{% if permissions.can_access_memory %}- ✅ Access memory{% else %}- ❌ Access memory{% endif %}

## Heartbeat

- **Enabled:** {{ heartbeat.enabled }}
- **Interval:** {{ heartbeat.interval_minutes }} minutes
- **Prompt:** {{ heartbeat.prompt }}

---

*This soul was auto-generated. Customize it to make this agent truly unique.*
'''


# Global registry instance
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _registry
    _registry = None
