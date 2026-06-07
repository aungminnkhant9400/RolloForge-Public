#!/usr/bin/env python3
"""
Agent creation CLI tool.

Usage:
    create_agent.py <name> --role <role> [options]
    create_agent.py --list-roles
    create_agent.py --example

Examples:
    create_agent.py "Code Reviewer" --role guardian --emoji 🛡️
    create_agent.py "Research Bot" --role researcher --tags "web,research"
    create_agent.py "Deploy Bot" --role executor --no-execute
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.agent_roles import AgentRole, ROLE_TEMPLATES
from rolloforge.agent_manager import AgentRegistry, get_registry


# ANSI colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def color(text: str, color_code: str) -> str:
    """Apply color to text."""
    return f"{color_code}{text}{Colors.END}"


def print_success(message: str) -> None:
    print(f"{color('✓', Colors.GREEN)} {message}")


def print_error(message: str) -> None:
    print(f"{color('✗', Colors.RED)} {message}", file=sys.stderr)


def print_info(message: str) -> None:
    print(f"{color('ℹ', Colors.BLUE)} {message}")


def list_roles() -> None:
    """Display available roles."""
    print(color("\n🎭 Available Agent Roles\n", Colors.BOLD + Colors.CYAN))
    print("=" * 60)
    
    for role in AgentRole:
        template = ROLE_TEMPLATES.get(role, {})
        emoji = template.get("emoji", "🤖")
        
        print(f"\n{emoji} {color(role.value.upper(), Colors.BOLD + Colors.YELLOW)}")
        print(f"   Mission: {template.get('mission', 'No description')}")
        print(f"   Tone: {template.get('tone', 'neutral')}")
        
        expertise = template.get("expertise", [])
        if expertise:
            print(f"   Expertise: {', '.join(expertise[:3])}")
    
    print()


def show_example() -> None:
    """Show example agent creation commands."""
    print(color("\n📚 Example Commands\n", Colors.BOLD + Colors.CYAN))
    print("=" * 60)
    
    examples = [
        ("Create a code review agent", 
         'create_agent.py "Code Guardian" --role guardian --emoji 🛡️ --tags "security,review"'),
        ("Create a research agent",
         'create_agent.py "Deep Diver" --role researcher --emoji 🔍 --no-execute'),
        ("Create an executor agent with limited scope",
         'create_agent.py "Deploy Bot" --role executor --emoji 🚀 --allowed-dirs "/home/ubuntu/app"'),
        ("Create an admin agent",
         'create_agent.py "Orchestrator" --role admin --emoji 👑'),
        ("Create a creative agent",
         'create_agent.py "Content Crafter" --role creative --emoji 🎨'),
        ("Create an analyst agent",
         'create_agent.py "Data Detective" --role analyst --emoji 📊'),
    ]
    
    for description, command in examples:
        print(f"\n{color(description, Colors.BOLD)}")
        print(f"  {color('$', Colors.CYAN)} {command}")
    
    print()


def create_agent(args: argparse.Namespace) -> int:
    """Create a new agent."""
    registry = get_registry()
    
    # Parse role
    try:
        role = AgentRole(args.role.lower())
    except ValueError:
        print_error(f"Invalid role: {args.role}")
        print_info(f"Run with --list-roles to see available roles")
        return 1
    
    # Build custom permissions
    custom_permissions = {}
    if args.no_read:
        custom_permissions["can_read_files"] = False
    if args.no_write:
        custom_permissions["can_write_files"] = False
    if args.no_execute:
        custom_permissions["can_execute_commands"] = False
    if args.no_browser:
        custom_permissions["can_use_browser"] = False
    if args.no_messages:
        custom_permissions["can_send_messages"] = False
    if args.no_memory:
        custom_permissions["can_access_memory"] = False
    if args.allowed_dirs:
        custom_permissions["allowed_directories"] = args.allowed_dirs
    if args.restricted_patterns:
        custom_permissions["restricted_patterns"] = args.restricted_patterns
    
    # Build custom heartbeat
    custom_heartbeat = {}
    if args.heartbeat_interval:
        custom_permissions["interval_minutes"] = args.heartbeat_interval
    if args.no_heartbeat:
        custom_permissions["enabled"] = False
    
    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    
    # Create the agent
    try:
        agent = registry.create(
            name=args.name,
            role=role,
            emoji=args.emoji,
            created_by=args.created_by or "cli",
            custom_permissions=custom_permissions or None,
            custom_heartbeat=custom_heartbeat or None,
            tags=tags,
            notes=args.notes or "",
        )
        
        print()
        print(color("=" * 60, Colors.CYAN))
        print(color(f"  Agent Created Successfully!", Colors.BOLD + Colors.GREEN))
        print(color("=" * 60, Colors.CYAN))
        print()
        print(f"  {agent.soul.emoji} Name:     {color(agent.soul.name, Colors.BOLD)}")
        print(f"    Role:     {agent.soul.role.value}")
        print(f"    ID:       {color(agent.id, Colors.YELLOW)}")
        print()
        print(f"  Mission:")
        print(f"    {agent.soul.mission}")
        print()
        print(f"  Voice:    {agent.soul.voice_description[:60]}...")
        print()
        
        if args.generate_soul:
            soul_path = PROJECT_ROOT / "agents" / agent.id / "SOUL.md"
            soul_path.parent.mkdir(parents=True, exist_ok=True)
            soul_content = registry.generate_soul_md(agent.id)
            if soul_content:
                soul_path.write_text(soul_content, encoding="utf-8")
                print_success(f"Generated SOUL.md: {soul_path}")
        
        if args.json_output:
            print()
            print(json.dumps(agent.to_dict(), indent=2))
        
        print()
        print_info(f"Use this agent with: forge agent start {agent.id}")
        
        return 0
        
    except Exception as e:
        print_error(f"Failed to create agent: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="create_agent.py",
        description="Create a new RolloForge agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  create_agent.py "My Bot" --role executor
  create_agent.py "Guardian" --role guardian --emoji 🛡️ --no-execute
  create_agent.py "Researcher" --role researcher --tags "web,scraping"
  create_agent.py --list-roles
  create_agent.py --example
        """
    )
    
    # Main arguments
    parser.add_argument("name", nargs="?", help="Name of the agent")
    parser.add_argument("--role", "-r", help="Agent role (use --list-roles to see options)")
    parser.add_argument("--emoji", "-e", help="Custom emoji for the agent")
    parser.add_argument("--created-by", "-c", help="Who is creating this agent")
    parser.add_argument("--tags", "-t", help="Comma-separated tags")
    parser.add_argument("--notes", "-n", help="Notes about the agent")
    
    # Permission flags
    permission_group = parser.add_argument_group("Permission Control")
    permission_group.add_argument("--no-read", action="store_true", help="Disable file reading")
    permission_group.add_argument("--no-write", action="store_true", help="Disable file writing")
    permission_group.add_argument("--no-execute", action="store_true", help="Disable command execution")
    permission_group.add_argument("--no-browser", action="store_true", help="Disable browser access")
    permission_group.add_argument("--no-messages", action="store_true", help="Disable message sending")
    permission_group.add_argument("--no-memory", action="store_true", help="Disable memory access")
    permission_group.add_argument("--allowed-dirs", nargs="+", help="Allowed directories for file operations")
    permission_group.add_argument("--restricted-patterns", nargs="+", help="Regex patterns to restrict")
    
    # Heartbeat flags
    heartbeat_group = parser.add_argument_group("Heartbeat Configuration")
    heartbeat_group.add_argument("--heartbeat-interval", type=int, help="Heartbeat interval in minutes")
    heartbeat_group.add_argument("--no-heartbeat", action="store_true", help="Disable heartbeat")
    
    # Output flags
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--generate-soul", "-s", action="store_true", help="Generate SOUL.md file")
    output_group.add_argument("--json-output", "-j", action="store_true", help="Output as JSON")
    
    # Info flags
    info_group = parser.add_argument_group("Information")
    info_group.add_argument("--list-roles", action="store_true", help="List available roles")
    info_group.add_argument("--example", action="store_true", help="Show example commands")
    
    args = parser.parse_args()
    
    # Handle info flags
    if args.list_roles:
        list_roles()
        return 0
    
    if args.example:
        show_example()
        return 0
    
    # Validate required args for creation
    if not args.name:
        print_error("Agent name is required (unless using --list-roles or --example)")
        parser.print_help()
        return 1
    
    if not args.role:
        print_error("Role is required. Use --list-roles to see available roles.")
        return 1
    
    return create_agent(args)


if __name__ == "__main__":
    raise SystemExit(main())
