# AI Harms Monitor — feedback-aligned static version

This version is designed to be simple to host/update and reflects feedback received by email.

## Feedback reflected

- Split `RA11a – Deepfake NCII and synthetic intimate image abuse` from `RA11b – Other AI-enabled VAWG behaviours` so NCII/deepfake content does not bury stalking, harassment, audio abuse and related VAWG harms.
- Added `RA11c – Child sexual abuse and exploitation` as a separate safeguarding view.
- Added two cross-cutting views:
  - realistic fakes/evidence/identity/public trust;
  - offender upskilling/capability uplift.
- No AI is integrated into the deployed tool. It uses rule-based RSS/search scoring only.
- Direct links are only displayed for domains in `public/trusted_domains.json`; other items show the headline and relevance evidence without a direct outbound link.
- Community/forum feeds are present but disabled by default to reduce noise and link/cyber risk.

## Local use

```bash
npm install
pip install feedparser
npm run scan
npm run dev
```

## Host on GitHub Pages

1. Create a GitHub repo and upload these files.
2. Go to Settings → Pages → Source → GitHub Actions.
3. Run the workflow: Actions → Update and publish AI Harms Monitor → Run workflow.

## Update relevance

Edit `public/harm_categories.json`:

- `must`: at least one must appear.
- `should`: harm-specific relevance terms.
- `uk_boost`: UK policy/operational terms.

Edit `public/trusted_domains.json` to control which result links are directly clickable.

Edit `public/sources.json` to enable/disable RSS sources.
