<div align="center">

# 🐺 Rafeeq Kernel v2.3.0

**Your Intelligent AI Companion — The Most Powerful Digital Ecosystem**

[![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)](https://github.com/omarlhlbwy441-netizen/dtr-n-fixed)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://docker.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](#english) | [العربية](#arabic)

</div>

---

<a name="english"></a>
## 🇬🇧 English

### Overview

Rafeeq (رفيق) is a self-evolving AI platform built with Python/FastAPI. It features multi-agent orchestration, autonomous code generation, GitHub integration, workspace management, and a complete cloud-native infrastructure.

### Features

- 🤖 **Multi-Agent System** — 10+ specialized AI agents
- 🧬 **Self-Evolution Engine** — Autonomous code generation & improvement
- 🐙 **GitHub Integration** — Auto-commit, sync, and deploy
- 🗄️ **PostgreSQL + Redis** — Production database & caching
- 📊 **Prometheus + Grafana** — Full monitoring & alerting
- 🔒 **Security** — Rate limiting, JWT auth, 2FA support
- 🐳 **Docker Ready** — One-command production deployment
- 🚀 **CI/CD** — GitHub Actions auto-deploy to Render

### Quick Start

```bash
# Clone
git clone https://github.com/omarlhlbwy441-netizen/dtr-n-fixed.git
cd dtr-n-fixed

# Setup (creates .env, SSL certs, directories)
make setup

# Development (hot-reload)
make dev

# Production
cp .env.example .env
# Edit .env with your values
make prod
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (443/80)                       │
│              SSL + Rate Limit + Compression                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    FastAPI Application                       │
│  Auth · Agents · Evolution · GitHub · Workspace · Health   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌─────────▼────────┐
│   PostgreSQL   │      │      Redis       │
│   (Users ·     │      │  (Cache ·        │
│    Sessions ·   │      │   Sessions ·     │
│    Metrics)    │      │   Rate Limits)   │
└────────────────┘      └──────────────────┘
        │                         │
┌───────▼────────┐      ┌─────────▼────────┐
│   Prometheus   │      │     Grafana      │
│  (Metrics)     │      │  (Dashboards)    │
└────────────────┘      └──────────────────┘
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | System health check |
| `GET /api/health/db` | Database health |
| `GET /api/health/redis` | Redis health |
| `GET /api/health/metrics` | Prometheus metrics |
| `POST /api/auth/login` | User authentication |
| `POST /api/auth/register` | User registration |
| `GET /api/agents` | List all agents |
| `POST /api/agents/{id}/chat` | Chat with agent |
| `POST /api/evolution/trigger` | Trigger evolution |
| `GET /api/github/status` | GitHub sync status |

### Environment Variables

See `.env.example` for all required variables.

### Monitoring

- **Grafana**: http://localhost:3000 (admin/rafeeq_grafana_2026)
- **Prometheus**: http://localhost:9090
- **API Docs**: https://localhost/api/docs

### Commands

```bash
make help      # Show all commands
make dev       # Start dev environment
make prod      # Start production
make test      # Run tests
make backup    # Run backup
make health    # Check health
make logs      # View logs
```

---

<a name="arabic"></a>
## 🇸🇦 العربية

### نظرة عامة

**رفيق** — رفيقك الذكي. أقوى نظام بيئي رقمي مع أقوى نواة ذكاء اصطناعي.

### الميزات

- 🤖 **نظام وكلاء متعدد** — 10+ وكيل متخصص
- 🧬 **محرك التطور الذاتي** — توليد أكواد وتحسين ذاتي
- 🐙 **تكامل GitHub** — رفع وتزامن تلقائي
- 🗄️ **PostgreSQL + Redis** — قاعدة بيانات وذاكرة تخزين مؤقت
- 📊 **Prometheus + Grafana** — مراقبة كاملة وتنبيهات
- 🔒 **أمان** — تقييد المعدل، مصادقة JWT، دعم 2FA
- 🐳 **Docker جاهز** — نشر إنتاجي بأمر واحد
- 🚀 **CI/CD** — نشر تلقائي عبر GitHub Actions

### البدء السريع

```bash
# استنساخ
git clone https://github.com/omarlhlbwy441-netizen/dtr-n-fixed.git
cd dtr-n-fixed

# إعداد
make setup

# تطوير
make dev

# إنتاج
make prod
```

### الأوامر

```bash
make help      # عرض جميع الأوامر
make dev       # بيئة التطوير
make prod      # بيئة الإنتاج
make test      # تشغيل الاختبارات
make backup    # نسخ احتياطي
make health    # فحص الصحة
make logs      # عرض السجلات
```

---

## License

MIT License — see [LICENSE](LICENSE) file.

## Credits

Built with ❤️ in Egypt 🇪🇬

> "من بعد فضل الله أشكر دولة مصر لأنها أتاحت لي فرصة لكي أقوم بهذا العمل"
