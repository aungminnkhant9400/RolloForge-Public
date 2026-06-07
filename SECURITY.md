# Security Best Practices

This document outlines the security measures and best practices for RolloForge to protect against supply chain attacks and other vulnerabilities.

## 🚨 Why This Matters

The [Axios supply chain attack](https://www.bleepingcomputer.com/news/security/axios-vulnerability-exposes-sensitive-data/) and similar incidents demonstrate how compromised dependencies can expose sensitive data. RolloForge implements multiple layers of security to mitigate these risks.

## 🔒 Security Tools

### 1. pip-audit (Python Dependencies)

Scans Python packages for known vulnerabilities in the PyPI advisory database.

```bash
# Install
pip install pip-audit

# Audit requirements.txt
pip-audit --requirement requirements.txt

# Audit installed packages
pip-audit

# With descriptions
pip-audit --desc
```

### 2. npm audit (Node.js Dependencies)

Built into npm, scans for known vulnerabilities in Node packages.

```bash
# From web/ directory
cd web

# Run audit
npm audit

# Fix automatically (careful!)
npm audit fix

# Check specific severity
npm audit --audit-level=high
```

### 3. Bandit (Python Security Linter)

Detects common security issues in Python code.

```bash
# Install
pip install bandit

# Scan directories
bandit -r rolloforge scripts config

# Detailed output
bandit -r . -f json -o bandit-report.json
```

### 4. Pre-commit Hook

Automatically runs security checks before each commit.

```bash
# Install hooks
./scripts/install-security.sh

# Or manually
cp .githooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

## 📋 Security Checklist

### Dependencies

- [ ] Pin exact versions in `requirements.txt` (use `==` not `>=`)
- [ ] Review new dependencies before adding
- [ ] Run `pip-audit` weekly or before releases
- [ ] Subscribe to security advisories for critical packages
- [ ] Keep `requests` updated (CVE history with this package)

### Secrets Management

- [ ] Never commit `.env` files
- [ ] Use environment variables for all secrets
- [ ] Rotate API keys quarterly
- [ ] Use different keys for dev/staging/prod
- [ ] Check for secrets before committing: `git diff --cached | grep -i password`

### Code Security

- [ ] Use parameterized queries (never string concat for SQL)
- [ ] Validate all user inputs
- [ ] Use HTTPS for all external requests
- [ ] Set security headers on web responses
- [ ] Sanitize data before logging

### CI/CD Security

- [ ] Review GitHub Actions for supply chain risks
- [ ] Pin Action versions to SHA, not tags
- [ ] Use least-privilege tokens
- [ ] Enable branch protection on main
- [ ] Require reviews before merging

## 🔄 Automated Security Workflow

### Daily (Automated)

GitHub Actions runs daily at 06:00 UTC:
- `pip-audit` on all requirements files
- `npm audit` on web dependencies
- `bandit` scan on Python code
- TruffleHog secrets scan

### On Every Commit (Pre-commit Hook)

Before any commit is allowed:
- Python dependency audit
- Node.js dependency audit
- Bandit security lint
- Secret detection in staged files

### On Pull Request

- Dependency review action
- Full security audit
- Block merge if high-severity vulnerabilities found

## 🛠️ Manual Security Commands

```bash
# Full security audit
./scripts/security-audit.sh

# Quick Python check
pip-audit --requirement requirements.txt --format json

# Check specific package
pip-audit --desc | grep requests

# Audit with fix suggestions
pip-audit --requirement requirements.txt --fix

# Web security
cd web && npm audit --audit-level=moderate
```

## 📊 Vulnerability Response

### Severity Levels

| Level | Response Time | Action |
|-------|--------------|--------|
| Critical | Immediate | Block commits, fix within 24h |
| High | 48 hours | Prioritize fix, temporary workarounds ok |
| Moderate | 1 week | Schedule fix in next sprint |
| Low | Next release | Address when convenient |

### When a Vulnerability is Found

1. **Don't panic** - Assess actual impact on RolloForge
2. **Check if exploitable** - Is the vulnerable code path used?
3. **Update dependency** - `pip install --upgrade package` or `npm update package`
4. **Test thoroughly** - Ensure fix doesn't break functionality
5. **Document** - Add to SECURITY.md if significant

## 🚫 Common Mistakes to Avoid

### Dependencies
- ❌ Using `pip install package` without pinning version
- ❌ Ignoring `npm audit` warnings
- ❌ Adding dependencies "just in case"
- ❌ Not reviewing transitive dependencies

### Secrets
- ❌ Hardcoding API keys in source
- ❌ Committing `.env` files
- ❌ Logging sensitive data
- ❌ Using production keys in dev

### Code
- ❌ `eval()` or `exec()` on user input
- ❌ Disabling SSL verification
- ❌ Storing passwords in plain text
- ❌ Trusting client-side validation

## 📚 Resources

- [PyPI Security](https://pypi.org/security/)
- [npm Security](https://www.npmjs.com/advisories)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Snyk Vulnerability DB](https://snyk.io/vuln/)
- [GitHub Security Advisories](https://github.com/advisories)

## 🆘 Security Incident Response

If you discover a security vulnerability in RolloForge:

1. **Do NOT open a public issue**
2. Email: [security contact]
3. Include: Description, impact, reproduction steps
4. Allow 72 hours for initial response
5. Coordinate disclosure timeline

---

*Last updated: March 2026*
