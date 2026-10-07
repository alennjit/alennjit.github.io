# Portfolio

Personal portfolio site for Alen Frashnishta. Plain HTML and CSS — no framework,
no client-side JavaScript, strict Content Security Policy.

Live: https://alennjit.github.io

## Adding or updating a project

1. Create `content/projects/<slug>.json` (lowercase-with-dashes). Copy an
   existing file as the template. Fields: `title`, `tagline`, `status`, `year`,
   `order`, `summary`, `problem`, `approach[]`, `highlights[]`, `stack[]`,
   `next[]`, `links[]`, `screenshots[]`.
2. Put screenshots in `assets/projects/<slug>/` and list them under
   `screenshots` (`file`, `alt`, `caption`). PNGs get their dimensions read
   automatically; for SVGs add `width` and `height`.
   Tip: capture at 2x device scale (retina) so they stay sharp.
3. Run `python build.py`. It regenerates the home-page cards, `projects/index.html`
   and one case-study page per project. Python standard library only.
4. Commit and push — GitHub Pages redeploys automatically.

To refresh a project's screenshots after it changes, replace the image files
(keep the same file names) and rebuild.

## Before publishing a screenshot

Check it for real client names, real email addresses, tokens, API keys and
internal hostnames. Use fictional data.

## Structure

```
index.html            home page (project cards are generated between markers)
styles.css            shared styles
build.py              static site generator
content/projects/     one JSON file per project
assets/projects/      screenshots, grouped by project slug
projects/             generated — do not edit by hand
```

## Custom domain later

Add a `CNAME` file containing the domain, set the same domain in the repo's
Pages settings, and point DNS at GitHub Pages. All links are relative, so
nothing else changes.
