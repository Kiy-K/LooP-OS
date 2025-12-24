# Security Policy

## Supported Versions

LooP is an experimental AI microkernel. We take security seriously, especially given the sandboxed execution environment for autonomous agents.

| Version | Supported          |
| ------- | ------------------ |
| 0.7.x   | :white_check_mark: |
| < 0.7.0 | :x:                |

## Security Considerations

LooP implements multiple security layers:

- **C++ Reinforced Sandbox**: Path traversal protection and virtual filesystem jail
- **RBAC Integration**: Role-based access control for network and system operations
- **Process Isolation**: Commands run with cleared environments and restricted paths
- **App Whitelisting**: Only authorized "Agent Apps" can be executed

However, as an **experimental project**, LooP should not be used in production environments or with untrusted agents without additional security hardening.

## Reporting a Vulnerability

If you discover a security vulnerability in LooP, please help us by reporting it responsibly.

### Where to Report

**Email**: khoitruong071510@gmail.com

**Subject**: `[SECURITY] LooP - Brief Description`

### What to Include

Please provide:
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Any suggested fixes (optional)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-2 weeks
  - High: 2-4 weeks
  - Medium/Low: Next release cycle

### What to Expect

**If Accepted:**
- We'll work on a fix and keep you updated
- Credit will be given in the CHANGELOG (unless you prefer anonymity)
- A security advisory will be published on GitHub
- Fix will be released in a patch version

**If Declined:**
- We'll explain why it's not considered a vulnerability
- Alternative perspectives or mitigations will be discussed

## Security Best Practices for Users

When using LooP:

1. **Sandbox Isolation**: Always run agents in the provided sandbox (`~/.loop/sandbox`)
2. **Network Controls**: Use RBAC permissions to limit network access (`manage_network`, `use_network`)
3. **API Key Security**: Never commit API keys; use `loop setup` to configure securely
4. **Plugin Vetting**: Only install plugins from trusted sources
5. **Stay Updated**: Keep LooP updated to the latest supported version

## Known Security Limitations

As an experimental OS, LooP has known limitations:

- **Not Production-Ready**: This is a research/educational project
- **Agent Trust Model**: Assumes LLM agents may be unpredictable
- **Sandbox Escape**: While hardened, no sandbox is 100% escape-proof
- **Network Layer**: Still in active development (v0.4.0)

## Security Updates

Security patches will be released as:
- Patch versions (e.g., 0.7.1) for minor issues
- Minor versions (e.g., 0.8.0) for significant security enhancements

Subscribe to releases on GitHub to stay notified.

---

**Note**: LooP is an experimental project. Use at your own risk in controlled environments only.
