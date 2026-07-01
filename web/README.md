# Course Web App

This Next.js app renders the root-level `s01_*` through `s20_*` course
chapters. The app does not treat `web/src/data/generated/*.json` or
`web/public/course-assets/` as source of truth; those files are generated from
the repository root.

## Local Development

```bash
npm ci
npm run dev
```

`npm run dev` runs `npm run extract` first, so edits to root chapter README
files, `code.py` files, or chapter SVG assets are copied into the web app
before the dev server starts.

## Updating Generated Course Data

After changing any root-level chapter content, run:

```bash
npm run extract
```

Commit the resulting updates under:

- `web/src/data/generated/`
- `web/public/course-assets/`

This keeps the web course aligned with the canonical root chapters and prevents
the site from showing stale code signatures, line counts, documentation text, or
chapter diagrams.

## Production Build

```bash
npm run build
```
