<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&duration=3000&pause=1000&color=00FF41&background=000000&center=true&vCenter=true&width=600&height=80&lines=JOBMONSTER;Autonomous+Job+Application+Agent;Scrape+%E2%86%92+Fill+%E2%86%92+Submit" alt="JOBMONSTER" />

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-45ba4b?style=for-the-badge&logo=playwright&logoColor=white)
![ATS](https://img.shields.io/badge/ATS-Greenhouse%20%7C%20Lever-FF6B35?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-8%2F10_Submitted-success?style=for-the-badge)

<br/>

> Give it a candidate profile. Walk away. Come back to submitted applications.

</div>

---

## What It Does

JOBMONSTER is a fully autonomous job application agent. It scrapes job listings from APIs, resolves aggregator URLs to the real employer ATS portals, fills every form field, uploads your resume, and submits — no human required.

**8 applications submitted** in a single run across Greenhouse portals (Culture Amp, Buildkite, Quantium). React Select dropdowns, file uploads, work authorisation fields — all handled.

---

## Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        JOBMONSTER PIPELINE                       │
└─────────────────────────────────────────────────────────────────┘

  [Adzuna API]  [JSearch API]  [Greenhouse]  [Lever]
       │               │             │           │
       └───────────────┴─────────────┴───────────┘
                               │
                         ┌─────▼─────┐
                         │   SCRAPE   │  pulls jobs from APIs
                         └─────┬─────┘
                               │
                         ┌─────▼─────┐
                         │   DEDUPE   │  company+title composite key
                         └─────┬─────┘
                               │
                         ┌─────▼─────┐
                         │   DETECT   │  trusted ATS vs aggregator
                         └─────┬─────┘
                               │
                   ┌───────────▼───────────┐
                   │   CHASE (Playwright)   │  follows redirect chains
                   └───────────┬───────────┘
                               │
                         ┌─────▼─────┐
                         │    PLAN    │  maps profile → form fields
                         └─────┬─────┘
                               │
                   ┌───────────▼───────────┐
                   │    FILL (Playwright)   │  text, dropdowns, files
                   └───────────┬───────────┘
                               │
                         ┌─────▼─────┐
                         │   SUBMIT   │  auto-submits, records result
                         └─────┬─────┘
                               │
                      data/results/run.json
```

---

## Demo Results

| Company | Role | Submitted | Fields Filled |
|---------|------|-----------|---------------|
| Culture Amp | AI Engineer - Applied AI | ✅ | 12 |
| Culture Amp | Lead AI Automation Engineer | ✅ | 12 |
| Culture Amp | Senior AI Engineer - Applied AI | ✅ | 12 |
| Buildkite | Staff ML Engineer | ✅ | 11 |
| Quantium | AI Education Programme Coordinator | ✅ | 11 |
| Quantium | Lead Data Scientist - Technical AI | ✅ | 11 |
| Quantium | Senior Full Stack Engineer (AI) | ✅ | 11 |
| Quantium | Senior Platform Engineer - AWS | ✅ | 11 |

---

## Quick Start

```bash
# Install
pip install -e .

# Set API keys
export ADZUNA_APP_ID="..."
export ADZUNA_APP_KEY="..."

# Scrape AU tech roles
python3 -m jobmonster.scrape --source ats --out data/jobs.json

# Apply — fully autonomous
python3 -m jobmonster.cli \
  --jobs data/jobs.json \
  --candidate examples/candidate.example.json \
  --resume /path/to/resume.pdf \
  --auto-submit \
  --limit 10 \
  --results-out data/results/run.json
```

---

## Candidate Profile

```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com",
  "phone": "0400000000",
  "location": "Melbourne, VIC",
  "linkedin": "https://linkedin.com/in/janesmith",
  "work_authorized": true,
  "needs_sponsorship": false,
  "notice_period": "Immediately",
  "salary_expectation": "120000",
  "custom_answers": {
    "why_this_role": "I build production AI systems and can contribute from day one."
  }
}
```

---

## Supported Platforms

| Platform | Mode | Status |
|----------|------|--------|
| Greenhouse | Full auto-fill + submit | ✅ Production |
| Lever | Form detection + fill | ✅ Production |
| Workday | Browser-assisted | ✅ |
| SmartRecruiters | Browser-assisted | ✅ |
| LiveHire / Humanforce | Browser-assisted | ✅ |
| Ashby | Browser-assisted | ✅ |
| Breezy | Browser-assisted | ✅ |
| JobAdder | Browser-assisted | ✅ |
| PageUp | Browser-assisted | ✅ |
| Adzuna / SEEK / Indeed / LinkedIn | Discovery only | ⛔ Not applied to |

---

## Architecture

```
jobmonster/
  scrapers/          # Adzuna, JSearch, Greenhouse, Lever, LinkedIn, SEEK, Jora
  adapters/          # Greenhouse, Lever, LinkedIn, generic; registry pattern
  scrape.py          # CLI: scrape and filter jobs
  cli.py             # CLI: plan + browser fill + submit
  run.py             # CLI: full end-to-end pipeline
  browser_assist.py  # Playwright fill engine
  detectors.py       # ATS platform detection
  chaser.py          # Redirect chain resolver
  resolver.py        # URL to trusted ATS resolver
  quota.py           # Monthly API usage tracker
  models.py          # Job, Candidate, ApplicationPlan dataclasses
  io.py              # Load/save helpers
```

## Design Principles

- **API-first** — no scraping aggregator HTML, no Cloudflare fights
- **Trusted ATS gate** — aggregator URLs skipped; only direct employer portals filled
- **No hardcoded credentials** — all secrets via environment variables
- **No stealth flags** — no webdriver masking or fingerprint spoofing
- **Quota tracking** — monthly API budgets with automatic blocking

---

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q jobmonster tests
```

---

<div align="center">

Built with [Claude Code](https://claude.ai/code) · Melbourne, AU

</div>
