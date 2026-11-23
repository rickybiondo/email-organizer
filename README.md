# Email Organizer

Automated Gmail classification and briefing system running on GitHub Actions.

## Features

- **Daily automation** (09:00 local time) via GitHub Actions
- **Rule-based classification** with extensible engine (ML-ready)
- **Gmail label hierarchy** (`Auto/Work`, `Auto/Personal`, `Auto/Newsletter`, etc.)
- **Morning briefing** delivered via email + web dashboard
- **Static dashboard** on GitHub Pages with charts and search
- **Zero infrastructure** — runs entirely on GitHub free tier
- **Learned mappings** — remembers sender→tag associations

## Architecture

```
GitHub Actions (scheduled) → Python script → Gmail API
    → Classify emails → Apply labels → Generate briefing
    → Send email → Update dashboard (GitHub Pages) → Commit data
```

## Quick Start

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/email-organizer.git
cd email-organizer
```

### 2. Create Google Cloud Project & OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → `email-organizer`
3. **Enable Gmail API**: APIs & Services → Library → Gmail API → Enable
4. **OAuth Consent Screen**: External → Add your email as test user
5. **Scopes**: Add:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.labels`
   - `https://www.googleapis.com/auth/gmail.send`
6. **Credentials** → Create OAuth Client ID → Desktop app → Download `credentials.json`

### 3. Generate Refresh Token (One-Time Local Setup)

```bash
# Place credentials.json in project root
pip install -r requirements.txt

python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.send'
])
creds = flow.run_local_server(port=0)
print('GMAIL_REFRESH_TOKEN:', creds.refresh_token)
print('GMAIL_CLIENT_ID:', creds.client_id)
print('GMAIL_CLIENT_SECRET:', creds.client_secret)
"
```

**Save the three values** — you'll need them for GitHub secrets.

### 4. Configure GitHub Repository Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `GMAIL_CLIENT_ID` | From step 3 |
| `GMAIL_CLIENT_SECRET` | From step 3 |
| `GMAIL_REFRESH_TOKEN` | From step 3 |
| `GMAIL_USER_EMAIL` | Your Gmail address (where briefing is sent) |
| `NTFY_TOPIC` | *(Optional)* ntfy.sh topic for failure alerts |

### 5. Enable GitHub Pages

Repo Settings → Pages → Source: **GitHub Actions**

### 6. Push & Run

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

Trigger manually: Actions → Daily Email Organization → Run workflow

## Customization

### Classification Rules

Edit `data/classification_rules.json` (committed after first run) or modify `src/config.py` defaults.

Rule types:
- **domain**: Match sender domain (`@company.com`)
- **header**: Check header existence/value (`List-Unsubscribe`, `Precedence: bulk`)
- **keyword**: Match subject/snippet patterns
- **address_book**: Match learned senders

Example:
```json
{
  "type": "domain",
  "pattern": "@myclient.com",
  "labels": ["Auto/Work", "Auto/Client-A"],
  "priority": 10
}
```

### Label Hierarchy

Default labels created automatically:
```
Auto/
├── Work/
│   ├── Client-A
│   └── Client-B
├── Personal
├── Newsletter
├── Promotion
├── Important
└── Unclassified
```

Modify `DEFAULT_LABELS` in `src/config.py`.

### Schedule

Edit `.github/workflows/daily.yml`:
```yaml
on:
  schedule:
    - cron: '0 7 * * *'  # 07:00 UTC = 09:00 CEST
```

### Dashboard

Static files in `dashboard/` — customize `index.html`, `app.js`, `style.css`.

Access at: `https://YOUR_USERNAME.github.io/email-organizer/`

## Data Persistence

All state stored in `data/` directory (committed daily):
- `processed_ids.json` — Set of processed message IDs
- `tag_mappings.json` — Learned sender→tags
- `classification_rules.json` — Active rules
- `latest.json` — Dashboard data
- `run_log.json` — Last 100 runs

## Local Development

```bash
# Install deps
pip install -r requirements.txt

# Run locally (requires credentials.json + token.json)
python -m src.main
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `invalid_grant` | Refresh token expired/revoked → Re-run step 3, update secret |
| Quota exceeded | Reduce `MAX_EMAILS_PER_RUN` in `config.py` |
| Labels not created | Check `gmail.modify` scope granted |
| Dashboard not updating | Verify Pages deployed from Actions; check `latest.json` |
| Emails not classified | Check `data/classification_rules.json` exists |

## Extending for ML

The classifier in `src/classifier.py` is designed for ML integration:

```python
# In classifier.py - add ML model
def classify(self, message):
    rule_result = self.engine.evaluate(message)
    ml_result = self.ml_model.predict(message)  # Future
    return combine(rule_result, ml_result)
```

## License

MIT — Use freely.

---

**Built with**: Python, Gmail API, GitHub Actions, GitHub Pages, Chart.js