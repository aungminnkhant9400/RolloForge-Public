#!/usr/bin/env python3
"""
RolloForge Dashboard Validator

Automated UI validation to catch data/UI mismatches before deployment.
This catches issues like the "Ignore bucket not showing" bug.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Project paths
PROJECT_ROOT = Path("/home/ubuntu/RolloForge")
WEB_DIR = PROJECT_ROOT / "web"
LIB_DIR = WEB_DIR / "lib"
APP_DIR = WEB_DIR / "app"

# Expected buckets in the UI
EXPECTED_BUCKETS = [
    "test_this_week",
    "build_later", 
    "archive",
    "ignore"
]

STAT_CARD_LABELS = [
    "Total Bookmarks",
    "Test This Week",
    "Build Later",
    "Archive",
    "Ignore"
]


@dataclass
class ValidationError:
    """A validation error found"""
    component: str
    severity: str  # ERROR, WARNING
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Dashboard validation results"""
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, component: str, message: str, details: dict = None):
        self.errors.append(ValidationError(
            component=component,
            severity="ERROR",
            message=message,
            details=details or {}
        ))
        self.valid = False
    
    def add_warning(self, component: str, message: str, details: dict = None):
        self.warnings.append(ValidationError(
            component=component,
            severity="WARNING",
            message=message,
            details=details or {}
        ))


class DashboardValidator:
    """Validates dashboard UI consistency"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.web_dir = self.project_root / "web"
        self.lib_dir = self.web_dir / "lib"
        self.app_dir = self.web_dir / "app"
        self.data: list[dict] = []
        self.analysis: list[dict] = []
        self.page_content: str = ""
        self.data_content: str = ""
        
    def load_files(self) -> ValidationResult:
        """Load all required files"""
        result = ValidationResult(valid=True)
        
        # Load data.json
        data_path = self.lib_dir / "data.json"
        if not data_path.exists():
            result.add_error("data.json", f"File not found: {data_path}")
            return result
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            result.stats["total_bookmarks"] = len(self.data)
        except json.JSONDecodeError as e:
            result.add_error("data.json", f"Invalid JSON: {e}")
            return result
        
        # Load analysis.json
        analysis_path = self.lib_dir / "analysis.json"
        if not analysis_path.exists():
            result.add_error("analysis.json", f"File not found: {analysis_path}")
            return result
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                self.analysis = json.load(f)
            result.stats["total_analysis"] = len(self.analysis)
        except json.JSONDecodeError as e:
            result.add_error("analysis.json", f"Invalid JSON: {e}")
            return result
        
        # Load page.tsx
        page_path = self.app_dir / "page.tsx"
        if not page_path.exists():
            result.add_error("page.tsx", f"File not found: {page_path}")
            return result
        with open(page_path, 'r', encoding='utf-8') as f:
            self.page_content = f.read()
            
        # Load data.ts
        data_ts_path = self.lib_dir / "data.ts"
        if not data_ts_path.exists():
            result.add_error("data.ts", f"File not found: {data_ts_path}")
            return result
        with open(data_ts_path, 'r', encoding='utf-8') as f:
            self.data_content = f.read()
            
        return result
    
    def validate_page_tsx(self) -> ValidationResult:
        """Validate page.tsx has all required components"""
        result = ValidationResult(valid=True)
        content = self.page_content
        
        # Check all 5 StatCard components are present
        stat_card_count = content.count("<StatCard")
        if stat_card_count != 5:
            result.add_error(
                "page.tsx",
                f"Expected 5 StatCard components, found {stat_card_count}",
                {"expected": 5, "found": stat_card_count}
            )
        
        # Check each bucket appears in page.tsx
        bucket_mappings = {
            "stats.total": "Total Bookmarks",
            "stats.test_this_week": "Test This Week",
            "stats.build_later": "Build Later",
            "stats.archive": "Archive",
            "stats.ignore": "Ignore"
        }
        
        for stat_ref, label in bucket_mappings.items():
            if stat_ref not in content:
                result.add_error(
                    "page.tsx",
                    f"Missing stat reference: {stat_ref} ({label})",
                    {"stat_ref": stat_ref, "label": label}
                )
            
            # Check the label appears
            if f'"{label}"' not in content and f"'{label}'" not in content:
                result.add_error(
                    "page.tsx",
                    f"Missing StatCard label: {label}",
                    {"label": label}
                )
        
        # Check getStats is called
        if "getStats()" not in content:
            result.add_error("page.tsx", "getStats() function not called")
        
        # Check imports
        required_imports = [
            "@/components/StatCard",
            "@/lib/data",
        ]
        for imp in required_imports:
            if imp not in content:
                result.add_error("page.tsx", f"Missing import: {imp}")
        
        result.stats["stat_card_count"] = stat_card_count
        return result
    
    def validate_data_ts(self) -> ValidationResult:
        """Validate data.ts has correct getStats implementation"""
        result = ValidationResult(valid=True)
        content = self.data_content
        
        # Check getStats function exists
        if "export function getStats()" not in content:
            result.add_error("data.ts", "getStats() function not exported")
            return result
        
        # Check all bucket types are handled in getStats
        required_buckets = [
            "test_this_week",
            "build_later",
            "archive",
            "ignore"
        ]
        
        for bucket in required_buckets:
            if f"recommendation_bucket === '{bucket}'" not in content:
                result.add_error(
                    "data.ts",
                    f"getStats() missing bucket filter for: {bucket}",
                    {"bucket": bucket}
                )
        
        # Check return object has all required fields
        if "return {" not in content or "total:" not in content:
            result.add_error("data.ts", "getStats() missing return statement with total")
        
        # Verify the calculation logic uses analysisMap
        if "analysisMap.get" not in content and "analysisMap.has" not in content:
            result.add_error("data.ts", "getStats() should use analysisMap for lookups")
        
        return result
    
    def validate_bucket_counts(self) -> ValidationResult:
        """Validate bucket counts sum correctly"""
        result = ValidationResult(valid=True)
        
        # Create analysis lookup
        analysis_by_id = {a.get("bookmark_id"): a for a in self.analysis}
        
        # Calculate counts manually
        counts = {
            "total": len(self.data),
            "test_this_week": 0,
            "build_later": 0,
            "archive": 0,
            "ignore": 0
        }
        
        for bookmark in self.data:
            bookmark_id = bookmark.get("id")
            analysis = analysis_by_id.get(bookmark_id)
            if analysis:
                bucket = analysis.get("recommendation_bucket")
                if bucket in counts:
                    counts[bucket] = counts.get(bucket, 0) + 1
        
        # Validate counts sum to analyzed total
        analyzed_total = counts["test_this_week"] + counts["build_later"] + counts["archive"] + counts["ignore"]
        
        if analyzed_total > counts["total"]:
            result.add_error(
                "bucket_counts",
                f"Analyzed bookmarks ({analyzed_total}) exceeds total ({counts['total']})",
                {"analyzed": analyzed_total, "total": counts["total"]}
            )
        
        result.stats["bucket_counts"] = counts
        result.stats["analyzed_count"] = analyzed_total
        result.stats["unanalyzed_count"] = counts["total"] - analyzed_total
        
        return result
    
    def validate_data_sync(self) -> ValidationResult:
        """Validate data.json and analysis.json are in sync"""
        result = ValidationResult(valid=True)
        
        # Get all bookmark IDs
        bookmark_ids = {b.get("id") for b in self.data if b.get("id")}
        
        # Get all analysis bookmark_ids
        analysis_ids = {a.get("bookmark_id") for a in self.analysis if a.get("bookmark_id")}
        
        # Check for orphaned analysis (analysis without bookmark)
        orphaned = analysis_ids - bookmark_ids
        if orphaned:
            result.add_warning(
                "data_sync",
                f"Found {len(orphaned)} analysis entries without matching bookmarks",
                {"orphaned_ids": list(orphaned)[:10]}  # Limit to first 10
            )
        
        # Check for bookmarks without analysis
        unanalyzed = bookmark_ids - analysis_ids
        if unanalyzed:
            result.stats["unanalyzed_bookmarks"] = len(unanalyzed)
            # This is just informational, not an error
        
        # Validate analysis buckets are valid
        valid_buckets = set(EXPECTED_BUCKETS)
        invalid_buckets = set()
        for analysis in self.analysis:
            bucket = analysis.get("recommendation_bucket")
            if bucket and bucket not in valid_buckets:
                invalid_buckets.add(bucket)
        
        if invalid_buckets:
            result.add_error(
                "data_sync",
                f"Invalid bucket values found: {invalid_buckets}",
                {"invalid": list(invalid_buckets)}
            )
        
        result.stats["bookmark_count"] = len(bookmark_ids)
        result.stats["analysis_count"] = len(analysis_ids)
        result.stats["orphaned_analysis"] = len(orphaned)
        
        return result
    
    def validate_types(self) -> ValidationResult:
        """Check for broken imports or missing types"""
        result = ValidationResult(valid=True)
        
        # Check data.ts has proper type exports
        required_types = [
            "export interface Bookmark",
            "export interface AnalysisResult",
            "export interface BookmarkWithAnalysis"
        ]
        
        for type_def in required_types:
            if type_def not in self.data_content:
                result.add_error("data.ts", f"Missing type definition: {type_def}")
        
        # Check recommendation_bucket type is correct
        if "recommendation_bucket: 'test_this_week' | 'build_later' | 'archive' | 'ignore'" not in self.data_content:
            result.add_warning(
                "data.ts",
                "Recommendation bucket type may not be properly constrained"
            )
        
        return result
    
    def run_all_validations(self) -> ValidationResult:
        """Run all validation checks"""
        # First load files
        result = self.load_files()
        if not result.valid:
            return result
        
        # Run all validations and merge results
        validations = [
            self.validate_page_tsx(),
            self.validate_data_ts(),
            self.validate_bucket_counts(),
            self.validate_data_sync(),
            self.validate_types()
        ]
        
        for v in validations:
            result.errors.extend(v.errors)
            result.warnings.extend(v.warnings)
            result.stats.update(v.stats)
        
        if result.errors:
            result.valid = False
            
        return result


def format_report(result: ValidationResult) -> str:
    """Format validation results for display"""
    lines = [
        "=" * 60,
        "DASHBOARD VALIDATION REPORT",
        "=" * 60,
        ""
    ]
    
    # Status
    if result.valid and not result.warnings:
        lines.append("✅ ALL CHECKS PASSED")
    elif result.valid:
        lines.append("⚠️  PASSED WITH WARNINGS")
    else:
        lines.append("❌ VALIDATION FAILED")
    
    lines.append("")
    
    # Stats
    lines.append("-" * 40)
    lines.append("STATISTICS:")
    lines.append("-" * 40)
    for key, value in result.stats.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for k, v in value.items():
                lines.append(f"    {k}: {v}")
        else:
            lines.append(f"  {key}: {value}")
    
    lines.append("")
    
    # Errors
    if result.errors:
        lines.append("-" * 40)
        lines.append(f"ERRORS ({len(result.errors)}):")
        lines.append("-" * 40)
        for i, error in enumerate(result.errors, 1):
            lines.append(f"\n{i}. [{error.component}] {error.severity}")
            lines.append(f"   {error.message}")
            if error.details:
                lines.append(f"   Details: {error.details}")
    
    # Warnings
    if result.warnings:
        lines.append("")
        lines.append("-" * 40)
        lines.append(f"WARNINGS ({len(result.warnings)}):")
        lines.append("-" * 40)
        for i, warning in enumerate(result.warnings, 1):
            lines.append(f"\n{i}. [{warning.component}]")
            lines.append(f"   {warning.message}")
            if warning.details:
                lines.append(f"   Details: {warning.details}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate RolloForge Dashboard")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Path to RolloForge project root"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output on failure"
    )
    
    args = parser.parse_args()
    
    validator = DashboardValidator(args.project_root)
    result = validator.run_all_validations()
    
    if args.json:
        output = {
            "valid": result.valid,
            "errors": [
                {"component": e.component, "message": e.message, "details": e.details}
                for e in result.errors
            ],
            "warnings": [
                {"component": w.component, "message": w.message, "details": w.details}
                for w in result.warnings
            ],
            "stats": result.stats
        }
        print(json.dumps(output, indent=2))
    else:
        report = format_report(result)
        if not args.quiet or not result.valid:
            print(report)
    
    # Exit with error code if validation failed
    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
