#!/usr/bin/env python3
"""
Tests for RolloForge Dashboard Validator

Run with: pytest tests/test_dashboard.py -v
Or: python3 tests/test_dashboard.py (runs simplified self-tests)
"""

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from dashboard_validator import (
    DashboardValidator,
    ValidationResult,
    ValidationError,
    EXPECTED_BUCKETS,
    format_report
)


def create_test_project(tmp_path, missing_ignore=False):
    """Create a test project structure"""
    web_dir = tmp_path / "web"
    lib_dir = web_dir / "lib"
    app_dir = web_dir / "app"
    lib_dir.mkdir(parents=True)
    app_dir.mkdir(parents=True)
    
    data = [
        {"id": "bookmark_1", "title": "Test 1", "bookmarked_at": "2026-03-01T00:00:00Z", "tags": []},
        {"id": "bookmark_2", "title": "Test 2", "bookmarked_at": "2026-03-02T00:00:00Z", "tags": []},
        {"id": "bookmark_3", "title": "Test 3", "bookmarked_at": "2026-03-03T00:00:00Z", "tags": []},
    ]
    (lib_dir / "data.json").write_text(json.dumps(data))
    
    analysis = [
        {"bookmark_id": "bookmark_1", "recommendation_bucket": "test_this_week"},
        {"bookmark_id": "bookmark_2", "recommendation_bucket": "build_later"},
        {"bookmark_id": "bookmark_3", "recommendation_bucket": "archive"},
    ]
    (lib_dir / "analysis.json").write_text(json.dumps(analysis))
    
    if missing_ignore:
        page_tsx = '''import { StatCard } from \'@/components/StatCard\';
import { getStats } from \'@/lib/data\';
export default function OverviewPage() {
  const stats = getStats();
  return (
    <div>
      <StatCard label="Total Bookmarks" value={stats.total} />
      <StatCard label="Test This Week" value={stats.test_this_week} />
      <StatCard label="Build Later" value={stats.build_later} />
      <StatCard label="Archive" value={stats.archive} />
    </div>
  );
}'''
    else:
        page_tsx = '''import { StatCard } from \'@/components/StatCard\';
import { getStats } from \'@/lib/data\';
export default function OverviewPage() {
  const stats = getStats();
  return (
    <div>
      <StatCard label="Total Bookmarks" value={stats.total} />
      <StatCard label="Test This Week" value={stats.test_this_week} />
      <StatCard label="Build Later" value={stats.build_later} />
      <StatCard label="Archive" value={stats.archive} />
      <StatCard label="Ignore" value={stats.ignore} />
    </div>
  );
}'''
    (app_dir / "page.tsx").write_text(page_tsx)
    
    data_ts = '''
export interface Bookmark { id: string; title: string; }
export interface AnalysisResult { bookmark_id: string; recommendation_bucket: 'test_this_week' | 'build_later' | 'archive' | 'ignore'; }
export interface BookmarkWithAnalysis extends Bookmark { analysis: AnalysisResult | null; }

export function getStats() {
  const analysisMap = new Map<string, AnalysisResult>();
  analysisMap.set("bookmark_1", { bookmark_id: "bookmark_1", recommendation_bucket: "test_this_week" });
  analysisMap.set("bookmark_2", { bookmark_id: "bookmark_2", recommendation_bucket: "build_later" });
  analysisMap.set("bookmark_3", { bookmark_id: "bookmark_3", recommendation_bucket: "archive" });
  
  return {
    total: 3,
    test_this_week: 1,
    build_later: 1,
    archive: 1,
    ignore: 0
  };
}
'''
    (lib_dir / "data.ts").write_text(data_ts)
    
    return tmp_path


def run_self_tests():
    """Run self-tests without pytest"""
    tests_passed = 0
    tests_failed = 0
    
    print("=" * 60)
    print("DASHBOARD VALIDATOR SELF-TESTS")
    print("=" * 60)
    print()
    
    # Test 1: Valid project
    print("Test 1: Valid project structure...")
    with tempfile.TemporaryDirectory() as tmp:
        project = create_test_project(Path(tmp), missing_ignore=False)
        validator = DashboardValidator(project)
        result = validator.load_files()
        if result.valid:
            result2 = validator.validate_page_tsx()
            result3 = validator.validate_data_sync()
            if result2.valid and len(result3.errors) == 0:
                print("  PASSED")
                tests_passed += 1
            else:
                print(f"  FAILED: page errors: {result2.errors}, sync errors: {result3.errors}")
                tests_failed += 1
        else:
            print(f"  FAILED loading files: {result.errors}")
            tests_failed += 1
    
    # Test 2: Missing ignore bucket
    print("Test 2: Missing ignore bucket detection...")
    with tempfile.TemporaryDirectory() as tmp:
        project = create_test_project(Path(tmp), missing_ignore=True)
        validator = DashboardValidator(project)
        validator.load_files()
        result = validator.validate_page_tsx()
        has_ignore_error = any("ignore" in e.message.lower() for e in result.errors)
        if has_ignore_error:
            print("  PASSED (correctly detected missing ignore bucket)")
            tests_passed += 1
        else:
            print(f"  FAILED: Expected error about ignore bucket, got: {result.errors}")
            tests_failed += 1
    
    # Test 3: Report formatting
    print("Test 3: Report formatting...")
    result = ValidationResult(valid=False)
    result.add_error("test", "Test error")
    result.stats["test_stat"] = 42
    report = format_report(result)
    if "FAILED" in report and "Test error" in report:
        print("  PASSED")
        tests_passed += 1
    else:
        print("  FAILED")
        tests_failed += 1
    
    # Test 4: Expected buckets constant
    print("Test 4: Expected buckets constant...")
    if ("test_this_week" in EXPECTED_BUCKETS and 
        "build_later" in EXPECTED_BUCKETS and
        "archive" in EXPECTED_BUCKETS and
        "ignore" in EXPECTED_BUCKETS and
        len(EXPECTED_BUCKETS) == 4):
        print("  PASSED")
        tests_passed += 1
    else:
        print(f"  FAILED: {EXPECTED_BUCKETS}")
        tests_failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    return tests_failed == 0


# Pytest-style tests (for when pytest is available)
class TestDashboardValidator:
    """Test cases for DashboardValidator"""
    
    def test_expected_buckets(self):
        """Test that expected buckets are defined correctly"""
        assert "test_this_week" in EXPECTED_BUCKETS
        assert "build_later" in EXPECTED_BUCKETS
        assert "archive" in EXPECTED_BUCKETS
        assert "ignore" in EXPECTED_BUCKETS
        assert len(EXPECTED_BUCKETS) == 4
    
    def test_validation_result_add_error(self):
        """Test adding errors to result"""
        result = ValidationResult(valid=True)
        result.add_error("test", "Test error", {"key": "value"})
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].component == "test"
        assert result.errors[0].severity == "ERROR"
    
    def test_format_report_with_errors(self):
        """Test formatting with errors"""
        result = ValidationResult(valid=False)
        result.add_error("page.tsx", "Missing StatCard")
        result.stats["total"] = 5
        
        report = format_report(result)
        
        assert "FAILED" in report
        assert "Missing StatCard" in report


if __name__ == "__main__":
    success = run_self_tests()
    sys.exit(0 if success else 1)
