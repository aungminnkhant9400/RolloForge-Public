#!/usr/bin/env python3
"""
RolloForge Nightly Build - Autonomous Code Shipping Workflow

Based on actionable-intelligence.md priority 7.0

This script runs autonomously to:
1. Check system health
2. Identify improvements from bookmarks/code patterns
3. Create branches and open PRs for changes
4. Generate morning reports
5. Maintain safety checks and rollback capability

Safety principles:
- NEVER push directly to main
- ALWAYS create branches/PRs for review
- Backup before any changes
- All actions are logged and reversible
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Add RolloForge to path
PROJECT_ROOT = Path("/home/ubuntu/RolloForge")
sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.storage import (
    load_bookmarks,
    load_analysis_results,
    save_bookmarks,
    save_analysis_results,
)
from rolloforge.models import Bookmark, AnalysisResult, ScoringInputs

# Configuration
REPO_DIR = PROJECT_ROOT
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
BACKUP_DIR = PROJECT_ROOT / ".nightly-backups"
LOG_DIR = PROJECT_ROOT / ".nightly-logs"
GITHUB_REPO = "aungminnkhant9400/RolloForge"
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Ensure directories exist
BACKUP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"nightly-{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nightly-build")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class HealthStatus:
    """Health check result"""
    component: str
    status: str  # OK, WARNING, CRITICAL
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Improvement:
    """Identified improvement opportunity"""
    category: str  # data_quality, code_quality, feature, documentation
    priority: int  # 1-10
    title: str
    description: str
    action_type: str  # auto_fix, pr_required, notify_only
    auto_fix_func: Optional[callable] = None
    pr_branch: Optional[str] = None


@dataclass
class BuildReport:
    """Nightly build report"""
    timestamp: str
    health_checks: list[HealthStatus] = field(default_factory=list)
    improvements_found: list[Improvement] = field(default_factory=list)
    auto_fixes_applied: list[dict] = field(default_factory=list)
    prs_created: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    overall_status: str = "SUCCESS"  # SUCCESS, PARTIAL, FAILED


# =============================================================================
# Safety & Backup System
# =============================================================================

class SafetyManager:
    """Manages backups and rollback capability"""
    
    def __init__(self, backup_dir: Path = BACKUP_DIR):
        self.backup_dir = backup_dir
        self.backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = backup_dir / self.backup_id
        
    def create_backup(self) -> Path:
        """Create backup of critical data files"""
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            DATA_DIR / "bookmarks_raw.json",
            DATA_DIR / "analysis_results.json",
            DATA_DIR / "seen_bookmarks.json",
        ]
        
        backed_up = []
        for file_path in files_to_backup:
            if file_path.exists():
                dest = self.backup_path / file_path.name
                shutil.copy2(file_path, dest)
                backed_up.append(file_path.name)
        
        # Store backup manifest
        manifest = {
            "timestamp": self.backup_id,
            "files": backed_up,
            "git_sha": self._get_git_sha(),
        }
        with open(self.backup_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"✓ Backup created: {self.backup_id} ({len(backed_up)} files)")
        return self.backup_path
    
    def _get_git_sha(self) -> str:
        """Get current git SHA"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_DIR,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    def rollback(self, backup_id: Optional[str] = None) -> bool:
        """Rollback to a specific backup"""
        backup_id = backup_id or self.backup_id
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        # Read manifest
        with open(backup_path / "manifest.json") as f:
            manifest = json.load(f)
        
        # Restore files
        for filename in manifest["files"]:
            src = backup_path / filename
            dest = DATA_DIR / filename
            if src.exists():
                shutil.copy2(src, dest)
                logger.info(f"✓ Restored: {filename}")
        
        logger.info(f"✓ Rollback complete to: {backup_id}")
        return True
    
    def list_backups(self) -> list[dict]:
        """List available backups"""
        backups = []
        for backup_path in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_path.is_dir() and (backup_path / "manifest.json").exists():
                with open(backup_path / "manifest.json") as f:
                    manifest = json.load(f)
                backups.append({
                    "id": backup_path.name,
                    "timestamp": manifest["timestamp"],
                    "files": manifest["files"],
                    "git_sha": manifest.get("git_sha", "unknown"),
                })
        return backups


# =============================================================================
# Health Check System
# =============================================================================

class HealthChecker:
    """Comprehensive health checking"""
    
    def __init__(self):
        self.checks: list[HealthStatus] = []
    
    def run_all_checks(self) -> list[HealthStatus]:
        """Run all health checks"""
        self.checks = []
        
        self._check_bookmark_analysis_sync()
        self._check_data_file_integrity()
        self._check_git_status()
        self._check_duplicate_bookmarks()
        self._check_missing_analyses()
        self._check_file_sizes()
        self._check_recent_activity()
        self._check_dashboard_ui()
        
        return self.checks
    
    def _check_bookmark_analysis_sync(self):
        """Check if bookmark count matches analysis count"""
        try:
            bookmarks = load_bookmarks()
            analyses = load_analysis_results()
            
            bm_count = len(bookmarks)
            an_count = len(analyses)
            diff = abs(bm_count - an_count)
            
            if diff == 0:
                status = "OK"
                message = f"Synced: {bm_count} bookmarks, {an_count} analyses"
            elif diff <= 5:
                status = "WARNING"
                message = f"Minor mismatch: {bm_count} bookmarks vs {an_count} analyses (diff: {diff})"
            else:
                status = "CRITICAL"
                message = f"Large mismatch: {bm_count} bookmarks vs {an_count} analyses (diff: {diff})"
            
            self.checks.append(HealthStatus(
                component="Bookmark/Analysis Sync",
                status=status,
                message=message,
                details={"bookmark_count": bm_count, "analysis_count": an_count, "diff": diff}
            ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Bookmark/Analysis Sync",
                status="CRITICAL",
                message=f"Check failed: {e}",
            ))
    
    def _check_data_file_integrity(self):
        """Check JSON validity of data files"""
        files_to_check = [
            DATA_DIR / "bookmarks_raw.json",
            DATA_DIR / "analysis_results.json",
            DATA_DIR / "seen_bookmarks.json",
        ]
        
        errors = []
        for filepath in files_to_check:
            if not filepath.exists():
                errors.append(f"{filepath.name}: MISSING")
                continue
            try:
                with open(filepath) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"{filepath.name}: INVALID JSON - {e}")
        
        if errors:
            self.checks.append(HealthStatus(
                component="Data File Integrity",
                status="CRITICAL",
                message="; ".join(errors),
                details={"errors": errors}
            ))
        else:
            self.checks.append(HealthStatus(
                component="Data File Integrity",
                status="OK",
                message="All data files valid",
            ))
    
    def _check_git_status(self):
        """Check git repository status"""
        try:
            # Check if we're on main
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=REPO_DIR,
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip()
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_DIR,
                capture_output=True,
                text=True,
            )
            uncommitted = result.stdout.strip()
            
            # Check unpushed commits
            result = subprocess.run(
                ["git", "log", "origin/main..HEAD", "--oneline"],
                cwd=REPO_DIR,
                capture_output=True,
                text=True,
            )
            unpushed = len([l for l in result.stdout.strip().split("\n") if l])
            
            if uncommitted and unpushed > 0:
                status = "WARNING"
                message = f"On {branch}, {len(uncommitted.split(chr(10)))} uncommitted changes, {unpushed} unpushed commits"
            elif uncommitted:
                status = "WARNING"
                message = f"On {branch}, {len(uncommitted.split(chr(10)))} uncommitted changes"
            elif unpushed > 0:
                status = "WARNING"
                message = f"On {branch}, {unpushed} unpushed commits"
            else:
                status = "OK"
                message = f"On {branch}, clean working directory"
            
            self.checks.append(HealthStatus(
                component="Git Status",
                status=status,
                message=message,
                details={"branch": branch, "uncommitted": bool(uncommitted), "unpushed": unpushed}
            ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Git Status",
                status="CRITICAL",
                message=f"Git check failed: {e}",
            ))
    
    def _check_duplicate_bookmarks(self):
        """Check for duplicate bookmarks by URL"""
        try:
            bookmarks = load_bookmarks()
            url_map: dict[str, list[str]] = {}
            
            for bm in bookmarks:
                # Normalize URL (remove query params, fragments)
                url = bm.url.split("?")[0].split("#")[0].rstrip("/")
                if url not in url_map:
                    url_map[url] = []
                url_map[url].append(bm.id)
            
            duplicates = {url: ids for url, ids in url_map.items() if len(ids) > 1}
            
            if duplicates:
                self.checks.append(HealthStatus(
                    component="Duplicate Bookmarks",
                    status="WARNING",
                    message=f"Found {len(duplicates)} duplicate URLs",
                    details={"duplicates": duplicates}
                ))
            else:
                self.checks.append(HealthStatus(
                    component="Duplicate Bookmarks",
                    status="OK",
                    message="No duplicate bookmarks found",
                ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Duplicate Bookmarks",
                status="CRITICAL",
                message=f"Check failed: {e}",
            ))
    
    def _check_missing_analyses(self):
        """Check for bookmarks without analyses"""
        try:
            bookmarks = load_bookmarks()
            analyses = load_analysis_results()
            
            bm_ids = {bm.id for bm in bookmarks}
            an_ids = {an.bookmark_id for an in analyses}
            
            missing = bm_ids - an_ids
            
            if missing:
                self.checks.append(HealthStatus(
                    component="Missing Analyses",
                    status="WARNING",
                    message=f"{len(missing)} bookmarks without analyses",
                    details={"missing_count": len(missing), "sample_ids": list(missing)[:5]}
                ))
            else:
                self.checks.append(HealthStatus(
                    component="Missing Analyses",
                    status="OK",
                    message="All bookmarks have analyses",
                ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Missing Analyses",
                status="CRITICAL",
                message=f"Check failed: {e}",
            ))
    
    def _check_file_sizes(self):
        """Check data file sizes"""
        try:
            files_to_check = [
                DATA_DIR / "bookmarks_raw.json",
                DATA_DIR / "analysis_results.json",
            ]
            
            warnings = []
            total_size = 0
            
            for filepath in files_to_check:
                if filepath.exists():
                    size_mb = filepath.stat().st_size / (1024 * 1024)
                    total_size += size_mb
                    if size_mb > 10:  # Warn if > 10MB
                        warnings.append(f"{filepath.name}: {size_mb:.1f}MB")
            
            if warnings:
                self.checks.append(HealthStatus(
                    component="File Sizes",
                    status="WARNING",
                    message="; ".join(warnings),
                    details={"warnings": warnings, "total_mb": round(total_size, 2)}
                ))
            else:
                self.checks.append(HealthStatus(
                    component="File Sizes",
                    status="OK",
                    message=f"Total: {total_size:.1f}MB",
                ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="File Sizes",
                status="CRITICAL",
                message=f"Check failed: {e}",
            ))
    
    def _check_recent_activity(self):
        """Check for recent bookmark activity"""
        try:
            bookmarks = load_bookmarks()
            
            if not bookmarks:
                self.checks.append(HealthStatus(
                    component="Recent Activity",
                    status="WARNING",
                    message="No bookmarks found",
                ))
                return
            
            # Sort by created_at
            sorted_bms = sorted(
                bookmarks,
                key=lambda bm: bm.created_at or "",
                reverse=True
            )
            
            def parse_dt(dt_str):
                """Parse ISO datetime string, ensuring UTC timezone if naive."""
                if not dt_str:
                    return None
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            
            now = datetime.now(timezone.utc)
            recent_count = len([bm for bm in bookmarks if bm.created_at and 
                              (now - parse_dt(bm.created_at)).days <= 7])
            
            self.checks.append(HealthStatus(
                component="Recent Activity",
                status="OK",
                message=f"{recent_count} bookmarks in last 7 days, {len(bookmarks)} total",
                details={"recent_7d": recent_count, "total": len(bookmarks)}
            ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Recent Activity",
                status="CRITICAL",
                message=f"Check failed: {e}",
            ))

    def _check_dashboard_ui(self):
        """Validate dashboard UI consistency - catches bugs like missing buckets"""
        try:
            # Import and run dashboard validator
            validator_path = REPO_DIR / "scripts" / "dashboard-validator.py"
            if not validator_path.exists():
                self.checks.append(HealthStatus(
                    component="Dashboard UI",
                    status="WARNING",
                    message="Dashboard validator not found",
                ))
                return
            
            # Run validator as subprocess
            result = subprocess.run(
                [sys.executable, str(validator_path), "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                self.checks.append(HealthStatus(
                    component="Dashboard UI",
                    status="CRITICAL",
                    message="Dashboard validator returned invalid output",
                    details={"stdout": result.stdout[:500], "stderr": result.stderr[:500]}
                ))
                return
            
            if output.get("valid") and not output.get("warnings"):
                stats = output.get("stats", {})
                bucket_counts = stats.get("bucket_counts", {})
                self.checks.append(HealthStatus(
                    component="Dashboard UI",
                    status="OK",
                    message=f"All 5 buckets present, {stats.get('total_bookmarks', 0)} bookmarks",
                    details={
                        "bucket_counts": bucket_counts,
                        "analyzed": stats.get("analyzed_count", 0),
                        "unanalyzed": stats.get("unanalyzed_count", 0)
                    }
                ))
            elif output.get("valid"):
                warnings = output.get("warnings", [])
                self.checks.append(HealthStatus(
                    component="Dashboard UI",
                    status="WARNING",
                    message=f"Dashboard valid with {len(warnings)} warnings",
                    details={"warnings": [w.get("message", str(w)) for w in warnings[:3]]}
                ))
            else:
                errors = output.get("errors", [])
                error_msgs = [e.get("message", str(e)) for e in errors[:3]]
                self.checks.append(HealthStatus(
                    component="Dashboard UI",
                    status="CRITICAL",
                    message=f"Dashboard UI issues: {'; '.join(error_msgs)}",
                    details={
                        "error_count": len(errors),
                        "errors": errors[:5]
                    }
                ))
        except subprocess.TimeoutExpired:
            self.checks.append(HealthStatus(
                component="Dashboard UI",
                status="WARNING",
                message="Dashboard validator timed out",
            ))
        except Exception as e:
            self.checks.append(HealthStatus(
                component="Dashboard UI",
                status="CRITICAL",
                message=f"Dashboard check failed: {e}",
            ))


# =============================================================================
# Improvement Detection
# =============================================================================

class ImprovementDetector:
    """Detects improvement opportunities from health checks and patterns"""
    
    def __init__(self, health_checks: list[HealthStatus]):
        self.health_checks = health_checks
        self.improvements: list[Improvement] = []
    
    def detect_all(self) -> list[Improvement]:
        """Detect all possible improvements"""
        self.improvements = []
        
        self._detect_duplicate_fixes()
        self._detect_missing_analysis_fixes()
        self._detect_code_improvements()
        self._detect_documentation_gaps()
        
        # Sort by priority (highest first)
        self.improvements.sort(key=lambda x: x.priority, reverse=True)
        return self.improvements
    
    def _detect_duplicate_fixes(self):
        """Detect if duplicates need fixing"""
        dup_check = next((c for c in self.health_checks if c.component == "Duplicate Bookmarks"), None)
        if dup_check and dup_check.status == "WARNING":
            duplicates = dup_check.details.get("duplicates", {})
            self.improvements.append(Improvement(
                category="data_quality",
                priority=8,
                title="Remove Duplicate Bookmarks",
                description=f"Found {len(duplicates)} duplicate URLs that should be merged",
                action_type="auto_fix",
                auto_fix_func=self._fix_duplicates,
            ))
    
    def _detect_missing_analysis_fixes(self):
        """Detect missing analyses"""
        missing_check = next((c for c in self.health_checks if c.component == "Missing Analyses"), None)
        if missing_check and missing_check.status == "WARNING":
            count = missing_check.details.get("missing_count", 0)
            self.improvements.append(Improvement(
                category="data_quality",
                priority=7,
                title=f"Analyze {count} Unanalyzed Bookmarks",
                description=f"{count} bookmarks are missing analysis results",
                action_type="auto_fix",
                auto_fix_func=self._create_missing_analyses,
            ))
    
    def _detect_code_improvements(self):
        """Detect potential code improvements"""
        # Check for common code patterns that could be improved
        improvements = []
        
        # Check if error handling could be improved
        scraper_path = PROJECT_ROOT / "rolloforge" / "scrapers"
        if scraper_path.exists():
            py_files = list(scraper_path.glob("*.py"))
            for py_file in py_files:
                content = py_file.read_text()
                # Look for bare except clauses
                if "except:" in content and "except Exception" not in content:
                    improvements.append(f"{py_file.name}: bare except clause")
        
        if improvements:
            self.improvements.append(Improvement(
                category="code_quality",
                priority=5,
                title="Improve Exception Handling",
                description=f"Found {len(improvements)} files with bare except clauses",
                action_type="pr_required",
            ))
    
    def _detect_documentation_gaps(self):
        """Detect missing documentation"""
        # Check if README is up to date with actual features
        readme_path = PROJECT_ROOT / "README.md"
        if readme_path.exists():
            readme_content = readme_path.read_text().lower()
            
            # Check for key features mentioned
            features_to_check = ["telegram", "scraper", "analysis", "dashboard"]
            missing_mentions = [f for f in features_to_check if f not in readme_content]
            
            if missing_mentions:
                self.improvements.append(Improvement(
                    category="documentation",
                    priority=4,
                    title="Update README Documentation",
                    description=f"README may be missing mentions of: {', '.join(missing_mentions)}",
                    action_type="pr_required",
                ))
    
    def _fix_duplicates(self) -> dict:
        """Auto-fix: Remove duplicate bookmarks"""
        bookmarks = load_bookmarks()
        analyses = load_analysis_results()
        
        # Group by normalized URL
        url_groups: dict[str, list[Bookmark]] = {}
        for bm in bookmarks:
            url = bm.url.split("?")[0].split("#")[0].rstrip("/")
            if url not in url_groups:
                url_groups[url] = []
            url_groups[url].append(bm)
        
        # Keep the first (oldest) bookmark, merge tags
        kept_bookmarks = []
        removed_ids = []
        
        for url, group in url_groups.items():
            if len(group) == 1:
                kept_bookmarks.append(group[0])
            else:
                # Sort by created_at, keep oldest
                sorted_group = sorted(group, key=lambda bm: bm.created_at or "")
                keeper = sorted_group[0]
                
                # Merge tags from duplicates
                all_tags = set(keeper.tags or [])
                for dup in sorted_group[1:]:
                    all_tags.update(dup.tags or [])
                    removed_ids.append(dup.id)
                
                keeper.tags = sorted(all_tags)
                kept_bookmarks.append(keeper)
        
        # Save cleaned bookmarks
        save_bookmarks(kept_bookmarks)
        
        # Remove orphaned analyses
        an_map = {an.bookmark_id: an for an in analyses}
        analyses = [an for an in analyses if an.bookmark_id not in removed_ids]
        save_analysis_results(analyses)
        
        return {
            "removed_duplicates": len(removed_ids),
            "kept_bookmarks": len(kept_bookmarks),
            "removed_ids": removed_ids[:10],  # First 10 for logging
        }
    
    def _create_missing_analyses(self) -> dict:
        """Auto-fix: Create placeholder analyses for missing bookmarks"""
        bookmarks = load_bookmarks()
        analyses = load_analysis_results()
        
        bm_ids = {bm.id for bm in bookmarks}
        an_ids = {an.bookmark_id for an in analyses}
        missing_ids = bm_ids - an_ids
        
        # Create basic analyses for missing bookmarks
        new_analyses = []
        for bm in bookmarks:
            if bm.id in missing_ids:
                analysis = AnalysisResult(
                    bookmark_id=bm.id,
                    summary="Auto-generated placeholder analysis",
                    recommendation_reason="Bookmark lacks detailed analysis. Assigned default priority pending manual review.",
                    key_insights=["Requires manual review"],
                    scoring_inputs=ScoringInputs(
                        relevance=5.0,
                        practical_value=5.0,
                        actionability=5.0,
                        stage_fit=5.0,
                        novelty=5.0,
                        excitement=5.0,
                        difficulty=5.0,
                        time_cost=5.0,
                    ),
                    worth_score=5.0,
                    effort_score=5.0,
                    priority_score=5.0,
                    recommendation_bucket="build_later",
                    analysis_source="nightly_auto",
                    analyzed_at=datetime.now(timezone.utc).isoformat(),
                )
                new_analyses.append(analysis)
        
        # Save combined analyses
        all_analyses = list(analyses) + new_analyses
        save_analysis_results(all_analyses)
        
        return {
            "created_analyses": len(new_analyses),
            "sample_ids": list(missing_ids)[:5],
        }


# =============================================================================
# Git & PR Management
# =============================================================================

class GitManager:
    """Manages git operations and PR creation"""
    
    def __init__(self):
        self.repo_dir = REPO_DIR
        self.github_repo = GITHUB_REPO
    
    def create_branch(self, branch_name: str, base: str = "main") -> bool:
        """Create a new branch from base"""
        try:
            # Ensure we're on base and up to date
            subprocess.run(
                ["git", "checkout", base],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "pull", "origin", base],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            
            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            
            logger.info(f"✓ Created branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """Stage and commit changes"""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return True
            
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            
            logger.info(f"✓ Committed: {message}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit: {e}")
            return False
    
    def push_branch(self, branch_name: str) -> bool:
        """Push branch to origin"""
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            
            logger.info(f"✓ Pushed branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push branch {branch_name}: {e}")
            return False
    
    def create_pr(self, branch_name: str, title: str, body: str) -> Optional[str]:
        """Create a pull request using gh CLI"""
        try:
            # Check if gh is installed and authenticated
            result = subprocess.run(
                ["gh", "auth", "status"],
                cwd=self.repo_dir,
                capture_output=True,
            )
            
            if result.returncode != 0:
                logger.warning("GitHub CLI not authenticated, skipping PR creation")
                return None
            
            # Create PR
            result = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", body],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                logger.info(f"✓ Created PR: {pr_url}")
                return pr_url
            else:
                logger.error(f"Failed to create PR: {result.stderr}")
                return None
        except FileNotFoundError:
            logger.warning("GitHub CLI not found, skipping PR creation")
            return None
    
    def checkout_main(self) -> bool:
        """Return to main branch"""
        try:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_dir,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout main: {e}")
            return False


# =============================================================================
# Report Generation
# =============================================================================

class ReportGenerator:
    """Generates morning reports"""
    
    def __init__(self, report: BuildReport):
        self.report = report
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report"""
        lines = []
        
        # Header
        lines.append("🌙 RolloForge Nightly Build Report")
        lines.append("=" * 50)
        lines.append(f"Generated: {self.report.timestamp}")
        lines.append(f"Status: {self.report.overall_status}")
        lines.append("")
        
        # Health Summary
        lines.append("📊 Health Check Summary")
        lines.append("-" * 30)
        
        critical = [c for c in self.report.health_checks if c.status == "CRITICAL"]
        warnings = [c for c in self.report.health_checks if c.status == "WARNING"]
        ok = [c for c in self.report.health_checks if c.status == "OK"]
        
        if critical:
            lines.append(f"❌ Critical: {len(critical)}")
            for check in critical:
                lines.append(f"   • {check.component}: {check.message}")
        
        if warnings:
            lines.append(f"⚠️  Warnings: {len(warnings)}")
            for check in warnings:
                lines.append(f"   • {check.component}: {check.message}")
        
        if ok:
            lines.append(f"✅ OK: {len(ok)}")
        
        lines.append("")
        
        # Improvements Found
        if self.report.improvements_found:
            lines.append("💡 Improvements Identified")
            lines.append("-" * 30)
            for imp in self.report.improvements_found[:5]:  # Top 5
                emoji = {"auto_fix": "🔧", "pr_required": "📋", "notify_only": "📢"}.get(imp.action_type, "•")
                lines.append(f"{emoji} [{imp.priority}/10] {imp.title}")
                lines.append(f"   {imp.description}")
            lines.append("")
        
        # Auto-fixes Applied
        if self.report.auto_fixes_applied:
            lines.append("🔧 Auto-Fixes Applied")
            lines.append("-" * 30)
            for fix in self.report.auto_fixes_applied:
                lines.append(f"✓ {fix['title']}: {fix.get('result', 'Success')}")
            lines.append("")
        
        # PRs Created
        if self.report.prs_created:
            lines.append("📋 Pull Requests Created")
            lines.append("-" * 30)
            for pr in self.report.prs_created:
                lines.append(f"• {pr['title']}")
                if pr.get('url'):
                    lines.append(f"  URL: {pr['url']}")
            lines.append("")
        
        # Errors
        if self.report.errors:
            lines.append("❌ Errors")
            lines.append("-" * 30)
            for error in self.report.errors:
                lines.append(f"• {error}")
            lines.append("")
        
        # Footer
        lines.append("=" * 50)
        lines.append("Review and merge PRs at your convenience.")
        lines.append("All changes are reversible from backups.")
        
        return "\n".join(lines)
    
    def generate_html_report(self) -> str:
        """Generate HTML report"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>RolloForge Nightly Build - {self.report.timestamp}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .status-{{ text-transform: uppercase; font-weight: bold; padding: 4px 12px; border-radius: 4px; }}
        .status-success {{ background: #d4edda; color: #155724; }}
        .status-partial {{ background: #fff3cd; color: #856404; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .check-ok {{ color: #28a745; }}
        .check-warning {{ color: #ffc107; }}
        .check-critical {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .improvement {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }}
        .priority-high {{ border-left: 4px solid #dc3545; }}
        .priority-medium {{ border-left: 4px solid #ffc107; }}
        .priority-low {{ border-left: 4px solid #28a745; }}
    </style>
</head>
<body>
    <h1>🌙 RolloForge Nightly Build Report</h1>
    <p><strong>Generated:</strong> {self.report.timestamp}</p>
    <p><strong>Status:</strong> <span class="status-{self.report.overall_status.lower()}">{self.report.overall_status}</span></p>
    
    <h2>📊 Health Checks</h2>
    <table>
        <tr><th>Component</th><th>Status</th><th>Message</th></tr>
"""
        
        for check in self.report.health_checks:
            status_class = f"check-{check.status.lower()}"
            html += f"        <tr><td>{check.component}</td><td class='{status_class}'>{check.status}</td><td>{check.message}</td></tr>\n"
        
        html += "    </table>\n"
        
        if self.report.improvements_found:
            html += "    <h2>💡 Improvements Identified</h2>\n"
            for imp in self.report.improvements_found:
                priority_class = "priority-high" if imp.priority >= 7 else "priority-medium" if imp.priority >= 4 else "priority-low"
                html += f"""
    <div class="improvement {priority_class}">
        <strong>[{imp.priority}/10] {imp.title}</strong> ({imp.action_type})
        <p>{imp.description}</p>
    </div>
"""
        
        if self.report.prs_created:
            html += "    <h2>📋 Pull Requests</h2>\n    <ul>\n"
            for pr in self.report.prs_created:
                html += f"        <li><a href='{pr.get('url', '#')}'>{pr['title']}</a></li>\n"
            html += "    </ul>\n"
        
        html += """
    <hr>
    <p><em>All changes are reversible from backups in .nightly-backups/</em></p>
</body>
</html>
"""
        return html
    
    def save_reports(self) -> dict[str, Path]:
        """Save reports to disk"""
        timestamp = datetime.now().strftime("%Y%m%d")
        
        text_path = REPORTS_DIR / f"nightly-report-{timestamp}.txt"
        html_path = REPORTS_DIR / f"nightly-report-{timestamp}.html"
        json_path = REPORTS_DIR / f"nightly-report-{timestamp}.json"
        
        text_path.write_text(self.generate_text_report())
        html_path.write_text(self.generate_html_report())
        
        # Save JSON for programmatic access
        json_data = {
            "timestamp": self.report.timestamp,
            "overall_status": self.report.overall_status,
            "health_checks": [
                {
                    "component": c.component,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.report.health_checks
            ],
            "improvements_found": len(self.report.improvements_found),
            "auto_fixes_applied": self.report.auto_fixes_applied,
            "prs_created": self.report.prs_created,
            "errors": self.report.errors,
        }
        json_path.write_text(json.dumps(json_data, indent=2))
        
        return {
            "text": text_path,
            "html": html_path,
            "json": json_path,
        }


# =============================================================================
# Main Build Orchestrator
# =============================================================================

class NightlyBuild:
    """Orchestrates the entire nightly build process"""
    
    def __init__(self, dry_run: bool = False, skip_auto_fix: bool = False):
        self.dry_run = dry_run
        self.skip_auto_fix = skip_auto_fix
        self.safety = SafetyManager()
        self.git = GitManager()
        self.report = BuildReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def run(self) -> BuildReport:
        """Execute the full nightly build"""
        logger.info("=" * 60)
        logger.info("🌙 RolloForge Nightly Build Starting")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("[DRY RUN MODE] No changes will be made")
        
        try:
            # Step 1: Create backup
            self._step_backup()
            
            # Step 2: Health checks
            self._step_health_checks()
            
            # Step 3: Detect improvements
            self._step_detect_improvements()
            
            # Step 4: Apply auto-fixes
            if not self.skip_auto_fix:
                self._step_apply_auto_fixes()
            
            # Step 5: Generate stats summary
            self._step_generate_stats()
            
            # Step 6: Create PRs for remaining improvements
            self._step_create_prs()
            
            # Step 7: Generate and save reports
            self._step_generate_reports()
            
            # Determine overall status
            if self.report.errors:
                self.report.overall_status = "FAILED" if any("CRITICAL" in e for e in self.report.errors) else "PARTIAL"
            
            logger.info("=" * 60)
            logger.info(f"✓ Nightly build complete: {self.report.overall_status}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.exception("Critical error during nightly build")
            self.report.errors.append(f"CRITICAL: {e}")
            self.report.overall_status = "FAILED"
            
            # Attempt rollback on critical failure
            logger.warning("Attempting rollback...")
            self.safety.rollback()
        
        return self.report
    
    def _step_backup(self):
        """Create safety backup"""
        logger.info("\n📦 Step 1: Creating backup...")
        if not self.dry_run:
            self.safety.create_backup()
        else:
            logger.info("[DRY RUN] Would create backup")
    
    def _step_health_checks(self):
        """Run all health checks"""
        logger.info("\n🔍 Step 2: Running health checks...")
        checker = HealthChecker()
        self.report.health_checks = checker.run_all_checks()
        
        for check in self.report.health_checks:
            emoji = {"OK": "✓", "WARNING": "⚠", "CRITICAL": "✗"}.get(check.status, "?")
            logger.info(f"  {emoji} {check.component}: {check.status} - {check.message}")
    
    def _step_detect_improvements(self):
        """Detect improvement opportunities"""
        logger.info("\n💡 Step 3: Detecting improvements...")
        detector = ImprovementDetector(self.report.health_checks)
        self.report.improvements_found = detector.detect_all()
        
        logger.info(f"  Found {len(self.report.improvements_found)} potential improvements")
        for imp in self.report.improvements_found:
            logger.info(f"  • [{imp.priority}/10] {imp.title} ({imp.action_type})")
    
    def _step_apply_auto_fixes(self):
        """Apply safe auto-fixes"""
        logger.info("\n🔧 Step 4: Applying auto-fixes...")
        
        auto_fixes = [imp for imp in self.report.improvements_found if imp.action_type == "auto_fix"]
        
        for imp in auto_fixes:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would apply: {imp.title}")
                continue
            
            try:
                if imp.auto_fix_func:
                    result = imp.auto_fix_func()
                    self.report.auto_fixes_applied.append({
                        "title": imp.title,
                        "result": result,
                    })
                    logger.info(f"  ✓ Applied: {imp.title}")
                    
                    # Commit the fix
                    branch_name = f"auto-fix/{self._sanitize_branch_name(imp.title)}"
                    if self.git.create_branch(branch_name):
                        self.git.commit_changes(f"Auto-fix: {imp.title}")
                        self.git.push_branch(branch_name)
                        
                        # Create PR
                        pr_url = self.git.create_pr(
                            branch_name=branch_name,
                            title=f"🤖 Auto-fix: {imp.title}",
                            body=f"""## Automated Fix

**Type:** {imp.category}
**Priority:** {imp.priority}/10

### Description
{imp.description}

### Changes
Auto-generated fix applied by nightly build system.

---
*This PR was created automatically. Review before merging.*
""",
                        )
                        
                        if pr_url:
                            self.report.prs_created.append({
                                "title": imp.title,
                                "url": pr_url,
                                "branch": branch_name,
                            })
                        
                        self.git.checkout_main()
                
            except Exception as e:
                logger.error(f"  ✗ Failed to apply {imp.title}: {e}")
                self.report.errors.append(f"Auto-fix failed: {imp.title} - {e}")
    
    def _step_generate_stats(self):
        """Generate stats summary"""
        logger.info("\n📊 Step 5: Generating stats summary...")
        try:
            result = subprocess.run(
                ["python3", str(PROJECT_ROOT / "scripts" / "generate_stats_summary.py")],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"  {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            logger.error(f"  ✗ Failed to generate stats summary: {e}")
            logger.error(e.stderr)
            self.report.errors.append(f"Stats summary generation failed: {e}")

    def _step_create_prs(self):
        """Create PRs for manual-review improvements"""
        logger.info("\n📋 Step 6: Creating PRs for manual improvements...")
        
        pr_items = [imp for imp in self.report.improvements_found if imp.action_type == "pr_required"]
        
        # For now, just log these - actual implementation would create placeholder PRs
        # or create GitHub issues for tracking
        for imp in pr_items[:3]:  # Limit to top 3
            logger.info(f"  • PR candidate: {imp.title}")
    
    def _step_generate_reports(self):
        """Generate and save reports"""
        logger.info("\n📝 Step 7: Generating reports...")
        generator = ReportGenerator(self.report)
        paths = generator.save_reports()
        
        logger.info(f"  ✓ Text report: {paths['text']}")
        logger.info(f"  ✓ HTML report: {paths['html']}")
        logger.info(f"  ✓ JSON report: {paths['json']}")
    
    def _sanitize_branch_name(self, name: str) -> str:
        """Convert title to valid branch name"""
        # Convert to lowercase, replace spaces/special chars with hyphens
        sanitized = re.sub(r'[^a-z0-9]+', '-', name.lower())
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Limit length
        return sanitized[:50] or "untitled"


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RolloForge Nightly Build - Autonomous code shipping workflow"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip-auto-fix",
        action="store_true",
        help="Skip applying auto-fixes (health checks only)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from last run without running build",
    )
    parser.add_argument(
        "--rollback",
        metavar="BACKUP_ID",
        help="Rollback to specific backup ID",
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available backups",
    )
    
    args = parser.parse_args()
    
    if args.list_backups:
        safety = SafetyManager()
        backups = safety.list_backups()
        print("Available backups:")
        for b in backups[:10]:
            print(f"  {b['id']} - {b['timestamp']} - {', '.join(b['files'])}")
        return
    
    if args.rollback:
        safety = SafetyManager()
        if safety.rollback(args.rollback):
            print(f"✓ Rolled back to: {args.rollback}")
        else:
            print(f"✗ Failed to rollback to: {args.rollback}")
        return
    
    # Run the build
    build = NightlyBuild(dry_run=args.dry_run, skip_auto_fix=args.skip_auto_fix)
    report = build.run()
    
    # Exit with appropriate code
    if report.overall_status == "FAILED":
        sys.exit(1)
    elif report.overall_status == "PARTIAL":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
