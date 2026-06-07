# CONTRIBUTING.md - Contributing to RolloForge

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Initial Setup
```bash
git clone https://github.com/aungminnkhant9400/RolloForge.git
cd RolloForge

# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js dependencies
cd web && npm install && cd ..

# Environment variables
cp .env.example .env
# Edit .env with your keys (NEVER commit this file)
```

### Verify Setup
```bash
# Test Python imports
python -c "from rolloforge.deepseek_analysis import deepseek_analyze_bookmark; print('OK')"

# Test Node build
cd web && npm run build && cd ..

# Run health check
python scripts/bookmark_health_dashboard.py
```

---

## Code Style Guide

### Python
- **PEP 8** compliant
- **Type hints** encouraged: `def func(x: str) -> int:`
- **Docstrings** for public functions
- **Max line length:** 100 characters

Example:
```python
def analyze_bookmark(text: str, title: str) -> dict:
    """
    Analyze bookmark content using DeepSeek API.
    
    Args:
        text: Full article text
        title: Article title
        
    Returns:
        Analysis result dict with keys: title, summary, tags, etc.
    """
    # Implementation
```

### TypeScript/React
- **Strict mode** enabled
- **Functional components** preferred
- **Props interfaces** required
- **No `any` types** (use `unknown` if needed)

Example:
```typescript
interface BookmarkCardProps {
  bookmark: Bookmark;
  analysis: AnalysisResult;
  onTagClick?: (tag: string) => void;
}

export function BookmarkCard({ bookmark, analysis }: BookmarkCardProps) {
  // Component
}
```

---

## Project Structure

```
rolloforge/
├── data/               # JSON data files (git-tracked)
├── web/                # Next.js dashboard
│   ├── app/            # Pages
│   ├── components/     # React components
│   └── lib/            # Build-time data copies
├── scripts/            # Python utilities
├── rolloforge/         # Python package
│   ├── scrapers/       # X, article scrapers
│   ├── analysis.py     # DeepSeek integration
│   └── utils.py        # Helper functions
└── docs/               # Documentation
```

---

## How to Add Features

### Adding a New CLI Command

1. Edit `forge.py`:
```python
@forge.command()
def my_command():
    """Description for help text."""
    # Implementation
    click.echo("Done!")
```

2. Test locally:
```bash
./forge my-command
```

3. Update docs in `docs/OPERATIONS.md`

### Adding a New Scraper

1. Create `rolloforge/scrapers/my_scraper.py`:
```python
def scrape_my_site(url: str) -> dict:
    """Scrape content from my-site.com."""
    # Implementation
    return {
        "success": True,
        "text": "...",
        "title": "...",
        "author": "..."
    }
```

2. Integrate in `save_bookmark.py`:
```python
if "my-site.com" in url:
    from rolloforge.scrapers.my_scraper import scrape_my_site
    scraped = scrape_my_site(url)
```

3. Add tests (see Testing section)

### Adding Dashboard Components

1. Create `web/components/MyComponent.tsx`:
```typescript
interface MyComponentProps {
  data: SomeType;
}

export function MyComponent({ data }: MyComponentProps) {
  return <div>{/* JSX */}</div>;
}
```

2. Import in page:
```typescript
import { MyComponent } from '@/components/MyComponent';

// Use in JSX
<MyComponent data={myData} />
```

3. Verify build: `cd web && npm run build`

---

## Testing Requirements

### Python Tests
Use **pytest**:
```python
# tests/test_analysis.py
def test_analysis_returns_dict():
    result = analyze_bookmark("test text", "Test Title")
    assert isinstance(result, dict)
    assert "summary" in result
```

Run tests:
```bash
pytest tests/
pytest tests/test_analysis.py -v
```

### Integration Tests
Test full pipeline:
```bash
# Test bookmark flow
python scripts/save_bookmark.py "https://example.com/test"
python scripts/analyze_bookmarks.py
python scripts/bookmark_health_dashboard.py
```

### Dashboard Tests
Build verification:
```bash
cd web
npm run build
# Should complete without errors
```

---

## PR Process

### Before Submitting
- [ ] Code follows style guide
- [ ] Tests pass (if applicable)
- [ ] Dashboard builds successfully
- [ ] Health check passes
- [ ] Documentation updated

### Branch Naming
```
feature/my-new-feature
fix/bug-description
docs/update-readme
```

### Commit Format
```
type: Short description

Longer explanation if needed.

- Bullet points for details
- Another point
```

Types: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

### PR Description Template
```markdown
## What
Brief description of changes.

## Why
Why this change was needed.

## Testing
How you tested it.

## Screenshots
If UI changes.
```

### Review Process
1. Automated checks must pass
2. One approval required
3. Address review comments
4. Squash and merge

---

## Questions?

- Check `docs/` first
- Look at existing code for patterns
- Ask in issues or discussions
