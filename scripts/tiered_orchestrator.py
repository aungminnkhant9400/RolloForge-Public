#!/usr/bin/env python3
"""
Tiered Worker Orchestrator with Provider Fallback
Implements combined solution: provider rotation + tiered workers + rate limiting
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TaskTier(Enum):
    """Worker tiers based on complexity and API usage."""
    LIGHT = "light"      # Simple checks, data validation
    MEDIUM = "medium"    # Analysis, documentation
    HEAVY = "heavy"      # Complex coding, multi-file changes


@dataclass
class WorkerTask:
    """Defines a worker task."""
    name: str
    tier: TaskTier
    description: str
    provider_priority: list[str]  # Ordered list of providers to try


# Define tiered worker tasks
TIERED_TASKS = {
    TaskTier.LIGHT: [
        WorkerTask("data-check", TaskTier.LIGHT, "Check data integrity", ["kimi", "openai"]),
        WorkerTask("duplicate-scan", TaskTier.LIGHT, "Scan for duplicates", ["kimi", "openai"]),
        WorkerTask("stats-update", TaskTier.LIGHT, "Update statistics", ["kimi", "openai"]),
    ],
    TaskTier.MEDIUM: [
        WorkerTask("bookmark-intelligence", TaskTier.MEDIUM, "Analyze bookmark patterns", ["kimi", "openai"]),
        WorkerTask("documentation", TaskTier.MEDIUM, "Update documentation", ["kimi", "openai"]),
        WorkerTask("automation-script", TaskTier.MEDIUM, "Build automation scripts", ["kimi", "openai"]),
    ],
    TaskTier.HEAVY: [
        WorkerTask("feature-builder", TaskTier.HEAVY, "Build new features", ["openai", "kimi"]),  # Prefer OpenAI for heavy tasks
        WorkerTask("code-refactor", TaskTier.HEAVY, "Refactor codebase", ["openai", "kimi"]),
    ]
}


class RateLimiter:
    """Simple rate limiter with exponential backoff."""
    
    def __init__(self, calls_per_minute: int = 10):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        self.consecutive_errors = 0
    
    def wait(self):
        """Wait appropriate time before next call."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            print(f"[RateLimiter] Sleeping {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.last_call_time = time.time()
    
    def on_error(self) -> float:
        """Handle error with exponential backoff."""
        self.consecutive_errors += 1
        backoff = min(2 ** self.consecutive_errors, 60)  # Max 60s backoff
        print(f"[RateLimiter] Error #{self.consecutive_errors}, backoff {backoff}s")
        return backoff
    
    def on_success(self):
        """Reset error count on success."""
        if self.consecutive_errors > 0:
            print(f"[RateLimiter] Reset after {self.consecutive_errors} errors")
            self.consecutive_errors = 0


def spawn_worker(task: WorkerTask, provider: str, rate_limiter: RateLimiter) -> dict:
    """Spawn a single worker with rate limiting and provider fallback."""
    
    print(f"[Orchestrator] Spawning {task.name} ({task.tier.value}) via {provider}")
    
    # Wait for rate limit
    rate_limiter.wait()
    
    # Build the task message
    task_message = f"""Tier {task.tier.value.upper()} task: {task.description}

Provider: {provider}
Rate limit: 10 calls/minute
Quality over quantity - take time to do this right.

Deliverables:
- Complete the task fully
- Test your work
- Report results clearly
"""
    
    # In a real implementation, this would spawn a subagent
    # For now, return the task configuration
    return {
        "task": task.name,
        "tier": task.tier.value,
        "provider": provider,
        "message": task_message,
        "status": "spawned"
    }


def orchestrate_build_cycle(preferred_provider: str = "kimi"):
    """Main orchestrator - implements combined solution."""
    
    print("=" * 60)
    print("Tiered Worker Orchestrator - Combined Solution")
    print("Provider rotation + Tiered workers + Rate limiting")
    print("=" * 60)
    
    # Create rate limiters per tier
    limiters = {
        TaskTier.LIGHT: RateLimiter(calls_per_minute=15),   # Light tasks can go faster
        TaskTier.MEDIUM: RateLimiter(calls_per_minute=10),  # Medium pace
        TaskTier.HEAVY: RateLimiter(calls_per_minute=5),    # Heavy tasks slower
    }
    
    results = []
    
    # Spawn LIGHT tier workers first (parallel, fast)
    print("\n[Phase 1] LIGHT tier workers (parallel)")
    for task in TIERED_TASKS[TaskTier.LIGHT]:
        # Try preferred provider first, fallback to others
        for provider in task.provider_priority:
            try:
                result = spawn_worker(task, provider, limiters[TaskTier.LIGHT])
                results.append(result)
                break
            except Exception as e:
                print(f"[Error] {provider} failed for {task.name}: {e}")
                continue
    
    # Spawn MEDIUM tier workers (parallel, moderate pace)
    print("\n[Phase 2] MEDIUM tier workers (parallel)")
    for task in TIERED_TASKS[TaskTier.MEDIUM]:
        for provider in task.provider_priority:
            try:
                result = spawn_worker(task, provider, limiters[TaskTier.MEDIUM])
                results.append(result)
                break
            except Exception as e:
                print(f"[Error] {provider} failed for {task.name}: {e}")
                continue
    
    # Spawn HEAVY tier workers (sequential to avoid overwhelming API)
    print("\n[Phase 3] HEAVY tier workers (sequential)")
    for task in TIERED_TASKS[TaskTier.HEAVY]:
        for provider in task.provider_priority:
            try:
                result = spawn_worker(task, provider, limiters[TaskTier.HEAVY])
                results.append(result)
                # Wait longer between heavy tasks
                time.sleep(12)  # Ensure we stay under rate limit
                break
            except Exception as e:
                print(f"[Error] {provider} failed for {task.name}: {e}")
                continue
    
    print("\n" + "=" * 60)
    print(f"Orchestration complete: {len(results)} workers spawned")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    results = orchestrate_build_cycle()
    
    # Output summary
    print("\nSpawned workers:")
    for r in results:
        print(f"  - {r['task']} ({r['tier']}) via {r['provider']}")
