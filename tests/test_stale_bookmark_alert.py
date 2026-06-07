#!/usr/bin/env python3
"""
Tests for stale_bookmark_alert.py

Run with: python -m pytest tests/test_stale_bookmark_alert.py -v
"""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from scripts.stale_bookmark_alert import StaleBookmarkChecker, StaleBookmark, main


class TestStaleBookmarkChecker:
    """Test suite for StaleBookmarkChecker."""
    
    def create_test_data(self, tmp_path):
        """Create test bookmark and analysis data."""
        now = datetime.now(timezone.utc)
        
        bookmarks = [
            {
                "id": "fresh_high_priority",
                "url": "https://example.com/fresh",
                "title": "Fresh High Priority",
                "bookmarked_at": now.isoformat(),
                "tags": ["test"],
            },
            {
                "id": "stale_high_priority",
                "url": "https://example.com/stale",
                "title": "Stale High Priority",
                "bookmarked_at": (now - timedelta(days=10)).isoformat(),
                "tags": ["important"],
            },
            {
                "id": "stale_low_priority",
                "url": "https://example.com/low",
                "title": "Stale Low Priority",
                "bookmarked_at": (now - timedelta(days=15)).isoformat(),
                "tags": [],
            },
            {
                "id": "build_later_stale",
                "url": "https://example.com/build",
                "title": "Build Later Stale",
                "bookmarked_at": (now - timedelta(days=20)).isoformat(),
                "tags": ["later"],
            },
        ]
        
        analyses = [
            {
                "bookmark_id": "fresh_high_priority",
                "priority_score": 8.0,
                "worth_score": 9.0,
                "recommendation_bucket": "test_this_week",
                "summary": "Fresh item",
            },
            {
                "bookmark_id": "stale_high_priority",
                "priority_score": 8.5,
                "worth_score": 9.0,
                "recommendation_bucket": "test_this_week",
                "summary": "Stale high priority item",
            },
            {
                "bookmark_id": "stale_low_priority",
                "priority_score": 3.0,
                "worth_score": 4.0,
                "recommendation_bucket": "test_this_week",
                "summary": "Stale low priority item",
            },
            {
                "bookmark_id": "build_later_stale",
                "priority_score": 7.0,
                "worth_score": 8.0,
                "recommendation_bucket": "build_later",
                "summary": "Stale build later item",
            },
        ]
        
        # Create temp data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        (data_dir / "bookmarks_raw.json").write_text(json.dumps(bookmarks))
        (data_dir / "analysis_results.json").write_text(json.dumps(analyses))
        
        return data_dir, bookmarks, analyses
    
    def test_load_data_success(self, tmp_path, monkeypatch):
        """Test successful data loading."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker()
        assert checker.load_data() is True
        assert len(checker.bookmarks) == 4
        assert len(checker.analyses) == 4
    
    def test_load_data_missing_file(self, tmp_path, monkeypatch):
        """Test handling of missing data files."""
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", tmp_path / "nonexistent")
        
        checker = StaleBookmarkChecker()
        assert checker.load_data() is False
    
    def test_parse_date_valid(self):
        """Test parsing valid ISO dates."""
        checker = StaleBookmarkChecker()
        
        # With timezone
        dt = checker.parse_date("2024-03-15T10:30:00+00:00")
        assert dt is not None
        assert dt.year == 2024
        
        # With Z suffix
        dt = checker.parse_date("2024-03-15T10:30:00Z")
        assert dt is not None
        
        # Without timezone
        dt = checker.parse_date("2024-03-15T10:30:00")
        assert dt is not None
    
    def test_parse_date_invalid(self):
        """Test parsing invalid dates."""
        checker = StaleBookmarkChecker()
        
        assert checker.parse_date(None) is None
        assert checker.parse_date("") is None
        assert checker.parse_date("invalid") is None
    
    def test_find_stale_bookmarks(self, tmp_path, monkeypatch):
        """Test finding stale bookmarks."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker(stale_days=7, priority_threshold=5.0)
        checker.load_data()
        
        stale = checker.find_stale_bookmarks()
        
        # Should find stale_high_priority (10 days, priority 8.5)
        # Should NOT find stale_low_priority (below threshold)
        # Should NOT find fresh_high_priority (not stale)
        assert len(stale) == 1
        assert stale[0].id == "stale_high_priority"
        assert stale[0].priority_score == 8.5
    
    def test_find_stale_bookmarks_multiple_buckets(self, tmp_path, monkeypatch):
        """Test finding stale bookmarks in multiple buckets."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker(
            stale_days=7,
            priority_threshold=5.0,
            buckets=["test_this_week", "build_later"]
        )
        checker.load_data()
        
        stale = checker.find_stale_bookmarks()
        
        # Should find both stale_high_priority and build_later_stale
        assert len(stale) == 2
        ids = {s.id for s in stale}
        assert "stale_high_priority" in ids
        assert "build_later_stale" in ids
    
    def test_generate_report_empty(self):
        """Test report generation with no stale bookmarks."""
        checker = StaleBookmarkChecker()
        report = checker.generate_report([])
        
        assert "No stale bookmarks found" in report
        assert "fresh" in report
    
    def test_generate_report_with_items(self, tmp_path, monkeypatch):
        """Test report generation with stale bookmarks."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker(stale_days=7, priority_threshold=5.0)
        checker.load_data()
        
        stale = checker.find_stale_bookmarks()
        report = checker.generate_report(stale)
        
        assert "STALE BOOKMARK ALERT" in report
        assert "stale_high_priority" not in report  # Shows title, not ID
        assert "Stale High Priority" in report
        assert "https://example.com/stale" in report
        assert "Priority: 8.5" in report
    
    def test_generate_telegram_message_empty(self):
        """Test Telegram message with no stale bookmarks."""
        checker = StaleBookmarkChecker()
        msg = checker.generate_telegram_message([])
        
        assert "No stale bookmarks" in msg
    
    def test_generate_telegram_message_with_items(self, tmp_path, monkeypatch):
        """Test Telegram message generation."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker(stale_days=7, priority_threshold=5.0)
        checker.load_data()
        
        stale = checker.find_stale_bookmarks()
        msg = checker.generate_telegram_message(stale)
        
        assert "Stale Bookmark" in msg
        assert "Stale High Priority" in msg
        assert "[Open]" in msg
    
    def test_find_auto_archive_candidates(self, tmp_path, monkeypatch):
        """Test finding auto-archive candidates."""
        data_dir, _, _ = self.create_test_data(tmp_path)
        monkeypatch.setattr("scripts.stale_bookmark_alert.DATA_DIR", data_dir)
        
        checker = StaleBookmarkChecker(stale_days=7, priority_threshold=5.0)
        checker.load_data()
        
        stale = checker.find_stale_bookmarks()
        candidates = checker.find_auto_archive_candidates(stale)
        
        # Only stale_high_priority with 10 days, less than AUTO_ARCHIVE_DAYS (30)
        assert len(candidates) == 0
        
        # Create a very stale bookmark
        very_stale = StaleBookmark(
            id="very_old",
            title="Very Old Bookmark",
            url="https://example.com/old",
            bucket="test_this_week",
            priority_score=6.0,
            worth_score=7.0,
            bookmarked_at=datetime.now(timezone.utc) - timedelta(days=35),
            days_stale=35,
        )
        candidates = checker.find_auto_archive_candidates([very_stale])
        assert len(candidates) == 1
    
    def test_stale_bookmark_to_dict(self):
        """Test StaleBookmark serialization."""
        now = datetime.now(timezone.utc)
        bookmark = StaleBookmark(
            id="test_id",
            title="Test Title",
            url="https://example.com",
            bucket="test_this_week",
            priority_score=7.5,
            worth_score=8.0,
            bookmarked_at=now,
            days_stale=10,
            tags=["test", "example"],
            summary="Test summary",
        )
        
        d = bookmark.to_dict()
        assert d["id"] == "test_id"
        assert d["title"] == "Test Title"
        assert d["priority_score"] == 7.5
        assert d["days_stale"] == 10


class TestMainFunction:
    """Test suite for main() function."""
    
    @patch("scripts.stale_bookmark_alert.StaleBookmarkChecker")
    def test_main_no_stale(self, mock_checker_class, monkeypatch, tmp_path):
        """Test main with no stale bookmarks."""
        mock_checker = MagicMock()
        mock_checker.load_data.return_value = True
        mock_checker.find_stale_bookmarks.return_value = []
        mock_checker_class.return_value = mock_checker
        
        # Mock sys.argv
        with patch.object(sys, 'argv', ['stale_bookmark_alert.py']):
            result = main()
        
        assert result == 0
    
    @patch("scripts.stale_bookmark_alert.StaleBookmarkChecker")
    def test_main_with_stale(self, mock_checker_class, monkeypatch, tmp_path):
        """Test main with stale bookmarks."""
        mock_checker = MagicMock()
        mock_checker.load_data.return_value = True
        mock_checker.find_stale_bookmarks.return_value = [
            StaleBookmark(
                id="test",
                title="Test",
                url="https://example.com",
                bucket="test_this_week",
                priority_score=6.0,
                worth_score=7.0,
                bookmarked_at=datetime.now(timezone.utc),
                days_stale=10,
            )
        ]
        mock_checker_class.return_value = mock_checker
        
        with patch.object(sys, 'argv', ['stale_bookmark_alert.py']):
            result = main()
        
        assert result == 1  # Exit code 1 when stale bookmarks found
    
    @patch("scripts.stale_bookmark_alert.StaleBookmarkChecker")
    def test_main_json_output(self, mock_checker_class, capsys):
        """Test main with JSON output."""
        from datetime import datetime, timezone
        mock_checker = MagicMock()
        mock_checker.load_data.return_value = True
        mock_checker.find_stale_bookmarks.return_value = []
        mock_checker.find_auto_archive_candidates.return_value = []
        mock_checker.now = datetime.now(timezone.utc)
        mock_checker.stale_days = 7
        mock_checker.priority_threshold = 5.0
        mock_checker.buckets = ["test_this_week"]
        mock_checker_class.return_value = mock_checker
        
        with patch.object(sys, 'argv', ['stale_bookmark_alert.py', '--json-output', '--quiet']):
            result = main()
        
        captured = capsys.readouterr()
        assert result == 0
        # JSON should be parseable
        output = json.loads(captured.out)
        assert "stale_count" in output
        assert output["stale_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
