# Deployment notes (unverified; card-free status must be checked by the user)

## Hugging Face Spaces

Create a Docker Space, expose port `7860`, add `FIXIE_LIVE_ENABLED`, CORS and any
provider values as Space secrets, and set `PORT=7860`. Space filesystem persistence
is not guaranteed; configure persistent storage before relying on SQLite replays.

## Render free tier

Create a Docker web service, set its port through `PORT`, and enter environment
values in the Render dashboard. Free-tier availability and card requirements are
unverified and must be checked by the user. Filesystem storage is ephemeral.

Never set `FIXIE_ALLOW_LOCAL=1` in deployment. Production live mode must use the
contree sandbox rather than local fixtures.
