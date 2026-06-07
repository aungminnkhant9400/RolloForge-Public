from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from enum import Enum


class AgentRole(str, Enum):
    """Predefined agent roles based on Claire Vo's model."""
    ADMIN = "admin"           # Sam - orchestrates, manages other agents
    RESEARCHER = "researcher"  # Finn - digs deep, finds information
    EXECUTOR = "executor"      # Howie - gets shit done, executes tasks
    CREATIVE = "creative"      # Artist - generates content, designs
    ANALYST = "analyst"        # Numbers - data analysis, reporting
    GUARDIAN = "guardian"      # Safety - reviews, security, compliance


class PermissionLevel(str, Enum):
    """Permission levels for agents."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass(slots=True)
class AgentPermissions:
    """Permission scoping for an agent."""
    # Tool permissions
    can_read_files: bool = True
    can_write_files: bool = True
    can_execute_commands: bool = True
    can_use_browser: bool = True
    can_send_messages: bool = True
    can_access_memory: bool = True
    
    # Channel permissions (channel_id -> permission_level)
    channels: dict[str, str] = field(default_factory=dict)
    
    # Tool-specific permissions (tool_name -> permission_level)
    tools: dict[str, str] = field(default_factory=dict)
    
    # Allowed directories (for file operations)
    allowed_directories: list[str] = field(default_factory=list)
    
    # Restricted patterns (regex patterns to block)
    restricted_patterns: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentPermissions":
        return cls(
            can_read_files=payload.get("can_read_files", True),
            can_write_files=payload.get("can_write_files", True),
            can_execute_commands=payload.get("can_execute_commands", True),
            can_use_browser=payload.get("can_use_browser", True),
            can_send_messages=payload.get("can_send_messages", True),
            can_access_memory=payload.get("can_access_memory", True),
            channels=payload.get("channels", {}),
            tools=payload.get("tools", {}),
            allowed_directories=payload.get("allowed_directories", []),
            restricted_patterns=payload.get("restricted_patterns", []),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HeartbeatConfig:
    """Heartbeat scheduler configuration."""
    enabled: bool = True
    interval_minutes: int = 30
    prompt: str = "Check for new tasks and handle any pending work."
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HeartbeatConfig":
        return cls(
            enabled=payload.get("enabled", True),
            interval_minutes=payload.get("interval_minutes", 30),
            prompt=payload.get("prompt", "Check for new tasks and handle any pending work."),
            max_retries=payload.get("max_retries", 3),
            retry_delay_seconds=payload.get("retry_delay_seconds", 60),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentSoul:
    """
    The "soul" of an agent - personality, voice, and core instructions.
    This is the template that defines how an agent behaves.
    """
    # Identity
    name: str
    role: AgentRole
    emoji: str = "🤖"
    avatar: str | None = None
    
    # Personality
    personality_traits: list[str] = field(default_factory=list)
    voice_description: str = ""
    tone: str = "professional"
    
    # Core directives
    mission: str = ""
    principles: list[str] = field(default_factory=list)
    
    # Specialization
    expertise: list[str] = field(default_factory=list)
    preferred_tools: list[str] = field(default_factory=list)
    
    # Context
    user_relationship: str = ""
    background: str = ""
    
    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentSoul":
        return cls(
            name=payload.get("name", "Unnamed Agent"),
            role=AgentRole(payload.get("role", "executor")),
            emoji=payload.get("emoji", "🤖"),
            avatar=payload.get("avatar"),
            personality_traits=payload.get("personality_traits", []),
            voice_description=payload.get("voice_description", ""),
            tone=payload.get("tone", "professional"),
            mission=payload.get("mission", ""),
            principles=payload.get("principles", []),
            expertise=payload.get("expertise", []),
            preferred_tools=payload.get("preferred_tools", []),
            user_relationship=payload.get("user_relationship", ""),
            background=payload.get("background", ""),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "emoji": self.emoji,
            "avatar": self.avatar,
            "personality_traits": self.personality_traits,
            "voice_description": self.voice_description,
            "tone": self.tone,
            "mission": self.mission,
            "principles": self.principles,
            "expertise": self.expertise,
            "preferred_tools": self.preferred_tools,
            "user_relationship": self.user_relationship,
            "background": self.background,
        }


@dataclass(slots=True)
class Agent:
    """
    A registered agent with full configuration.
    """
    # Identity
    id: str
    soul: AgentSoul
    
    # Configuration
    permissions: AgentPermissions
    heartbeat: HeartbeatConfig
    
    # Metadata
    created_at: str
    updated_at: str
    created_by: str = "system"
    
    # State
    is_active: bool = True
    last_heartbeat: str | None = None
    total_tasks_completed: int = 0
    
    # Runtime
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    
    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Agent":
        return cls(
            id=payload.get("id", ""),
            soul=AgentSoul.from_dict(payload.get("soul", {})),
            permissions=AgentPermissions.from_dict(payload.get("permissions", {})),
            heartbeat=HeartbeatConfig.from_dict(payload.get("heartbeat", {})),
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", ""),
            created_by=payload.get("created_by", "system"),
            is_active=payload.get("is_active", True),
            last_heartbeat=payload.get("last_heartbeat"),
            total_tasks_completed=payload.get("total_tasks_completed", 0),
            version=payload.get("version", "1.0.0"),
            tags=payload.get("tags", []),
            notes=payload.get("notes", ""),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "soul": self.soul.to_dict(),
            "permissions": self.permissions.to_dict(),
            "heartbeat": self.heartbeat.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "last_heartbeat": self.last_heartbeat,
            "total_tasks_completed": self.total_tasks_completed,
            "version": self.version,
            "tags": self.tags,
            "notes": self.notes,
        }


# ============================================================================
# ROLE TEMPLATES
# ============================================================================

ROLE_TEMPLATES: dict[AgentRole, dict[str, Any]] = {
    AgentRole.ADMIN: {
        "emoji": "👑",
        "personality_traits": [
            "strategic thinker",
            "orchestrator",
            "delegator",
            "big picture focused"
        ],
        "voice_description": "Confident, decisive, clear. Speaks with authority but doesn't micromanage.",
        "tone": "commanding but collaborative",
        "mission": "Coordinate other agents, make high-level decisions, and ensure the system runs smoothly.",
        "principles": [
            "Delegate effectively - don't do everything yourself",
            "Know when to escalate and when to handle",
            "Keep the big picture in mind",
            "Trust your team of agents"
        ],
        "expertise": ["system architecture", "coordination", "prioritization", "resource management"],
        "preferred_tools": ["process", "exec", "memory_search", "message"],
    },
    AgentRole.RESEARCHER: {
        "emoji": "🔍",
        "personality_traits": [
            "curious",
            "thorough",
            "skeptical",
            "detail-oriented"
        ],
        "voice_description": "Inquisitive, methodical, precise. Asks good questions and digs deep.",
        "tone": "analytical and curious",
        "mission": "Find information, validate sources, and provide comprehensive research on any topic.",
        "principles": [
            "Verify your sources",
            "Go deeper than surface level",
            "Present findings clearly",
            "Admit when you don't know"
        ],
        "expertise": ["web research", "data gathering", "source verification", "synthesis"],
        "preferred_tools": ["web_search", "web_fetch", "browser", "pdf", "read"],
    },
    AgentRole.EXECUTOR: {
        "emoji": "⚡",
        "personality_traits": [
            "action-oriented",
            "reliable",
            "efficient",
            "pragmatic"
        ],
        "voice_description": "Direct, no-nonsense, focused. Gets straight to the point and gets things done.",
        "tone": "direct and efficient",
        "mission": "Execute tasks, implement solutions, and ship code. Focus on delivery.",
        "principles": [
            "Done is better than perfect",
            "Ship early, ship often",
            "Fix forward",
            "Measure twice, cut once"
        ],
        "expertise": ["coding", "automation", "deployment", "tool integration"],
        "preferred_tools": ["exec", "edit", "write", "read", "process"],
    },
    AgentRole.CREATIVE: {
        "emoji": "🎨",
        "personality_traits": [
            "imaginative",
            "playful",
            "experimental",
            "aesthetic"
        ],
        "voice_description": "Expressive, visual, playful. Brings ideas to life with style.",
        "tone": "creative and expressive",
        "mission": "Generate content, design solutions, and bring creative vision to projects.",
        "principles": [
            "Beauty matters",
            "Experiment freely",
            "Inspire through creation",
            "Constraints breed creativity"
        ],
        "expertise": ["content creation", "design", "storytelling", "branding"],
        "preferred_tools": ["write", "image", "canvas", "tts"],
    },
    AgentRole.ANALYST: {
        "emoji": "📊",
        "personality_traits": [
            "logical",
            "data-driven",
            "objective",
            "systematic"
        ],
        "voice_description": "Precise, evidence-based, measured. Lets the data speak.",
        "tone": "analytical and objective",
        "mission": "Analyze data, identify patterns, and provide actionable insights.",
        "principles": [
            "Data over opinions",
            "Correlation ≠ causation",
            "Show your work",
            "Question assumptions"
        ],
        "expertise": ["data analysis", "statistics", "visualization", "reporting"],
        "preferred_tools": ["read", "exec", "write", "browser"],
    },
    AgentRole.GUARDIAN: {
        "emoji": "🛡️",
        "personality_traits": [
            "vigilant",
            "cautious",
            "ethical",
            "protective"
        ],
        "voice_description": "Careful, warning when needed, principled. Speaks up about risks.",
        "tone": "cautious and principled",
        "mission": "Review work, identify risks, and ensure safety and compliance.",
        "principles": [
            "Safety first",
            "Ask before acting",
            "Document risks",
            "Better safe than sorry"
        ],
        "expertise": ["security", "compliance", "risk assessment", "review"],
        "preferred_tools": ["read", "memory_search", "message"],
    },
}


def get_role_template(role: AgentRole) -> dict[str, Any]:
    """Get the template for a specific role."""
    return ROLE_TEMPLATES.get(role, ROLE_TEMPLATES[AgentRole.EXECUTOR]).copy()


def get_default_permissions(role: AgentRole) -> AgentPermissions:
    """Get default permissions for a role."""
    base = AgentPermissions()
    
    if role == AgentRole.ADMIN:
        base.can_execute_commands = True
        base.can_write_files = True
        base.can_send_messages = True
    elif role == AgentRole.RESEARCHER:
        base.can_execute_commands = False
        base.can_write_files = True  # For research notes
        base.can_send_messages = False
    elif role == AgentRole.EXECUTOR:
        base.can_execute_commands = True
        base.can_write_files = True
        base.can_send_messages = True
    elif role == AgentRole.CREATIVE:
        base.can_execute_commands = False
        base.can_write_files = True
        base.can_send_messages = True
    elif role == AgentRole.ANALYST:
        base.can_execute_commands = False
        base.can_write_files = True
        base.can_send_messages = False
    elif role == AgentRole.GUARDIAN:
        base.can_execute_commands = False
        base.can_write_files = True  # For reports
        base.can_send_messages = True  # To warn
        base.can_read_files = True
    
    return base


def get_default_heartbeat(role: AgentRole) -> HeartbeatConfig:
    """Get default heartbeat config for a role."""
    configs = {
        AgentRole.ADMIN: HeartbeatConfig(interval_minutes=60, prompt="Review agent statuses and coordinate any needed actions."),
        AgentRole.RESEARCHER: HeartbeatConfig(interval_minutes=120, prompt="Check for new research tasks and update ongoing investigations."),
        AgentRole.EXECUTOR: HeartbeatConfig(interval_minutes=30, prompt="Check for pending tasks and execute them."),
        AgentRole.CREATIVE: HeartbeatConfig(interval_minutes=240, prompt="Check for creative requests and inspiration sources."),
        AgentRole.ANALYST: HeartbeatConfig(interval_minutes=180, prompt="Check for data to analyze and update reports."),
        AgentRole.GUARDIAN: HeartbeatConfig(interval_minutes=360, prompt="Review recent actions for safety and compliance."),
    }
    return configs.get(role, HeartbeatConfig())
