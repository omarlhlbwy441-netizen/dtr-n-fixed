# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.3.x   | :white_check_mark: |
| 2.2.x   | :white_check_mark: |
| < 2.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please email us at **security@rafeeq.ai**.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Possible impact
- Suggested fix (if any)

We will respond within 48 hours and aim to release a patch within 7 days.

## Security Measures

- All passwords hashed with bcrypt
- JWT tokens with expiration
- Rate limiting on all endpoints
- SQL injection protection via parameterized queries
- XSS protection via security headers
- HTTPS enforcement in production
- Regular dependency updates via Dependabot
- CodeQL security scanning on every push

## Responsible Disclosure

We follow responsible disclosure practices. Please do not publicly disclose vulnerabilities until we have released a fix.
