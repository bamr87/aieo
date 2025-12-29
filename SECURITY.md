# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it privately using one of the following methods:

### Preferred Method

Email: [INSERT SECURITY EMAIL]

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### Alternative Methods

- Open a [GitHub Security Advisory](https://github.com/your-username/aieo/security/advisories/new)
- Contact maintainers through GitHub (if you have access)

## Security Best Practices

### API Keys

- **Never commit API keys** to the repository
- Use environment variables (`.env` file)
- Rotate keys regularly
- Use different keys for development and production

### Dependencies

- Keep dependencies up to date
- Review security advisories regularly
- Use `pip-audit` or `npm audit` to check for vulnerabilities

### Data Handling

- User content is processed in-memory when possible
- Content is encrypted at rest (AES-256)
- Content is encrypted in transit (TLS 1.3)
- User-controlled retention (default: 30 days)

### Authentication

- API keys are hashed (SHA256) before storage
- Rate limiting is enforced
- Input validation and sanitization on all endpoints

## Security Checklist

When contributing, ensure:

- [ ] No hardcoded credentials or API keys
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (use parameterized queries)
- [ ] XSS prevention (sanitize user content)
- [ ] CSRF protection (if applicable)
- [ ] Rate limiting implemented
- [ ] Error messages don't leak sensitive information
- [ ] Dependencies are up to date
- [ ] Security headers are set correctly

## Known Security Considerations

### AI Service Integration

- API keys must be kept secure
- Rate limits may apply from AI service providers
- Content sent to AI services may be logged by providers

### Database

- Use parameterized queries (SQLAlchemy handles this)
- Database credentials should be in environment variables
- Regular backups recommended

### Docker

- Keep Docker images updated
- Use non-root user in containers when possible
- Review docker-compose.yml for exposed ports

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.1)
- Documented in CHANGELOG.md
- Tagged with `security` label

## Disclosure Policy

- Vulnerabilities will be disclosed after a fix is available
- A CVE will be requested for critical vulnerabilities
- Users will be notified through GitHub releases

## Security Audit

Regular security audits are recommended:
- Dependency scanning
- Code review
- Penetration testing (for production deployments)

Thank you for helping keep AIEO secure!

