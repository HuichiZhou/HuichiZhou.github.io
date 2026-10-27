# Huichi Zhou — personal website

A static academic homepage with research-area browsing, publication search, and per-paper Google Scholar citation links. All publication content and counts are rendered into HTML, so they remain available without JavaScript or third-party requests.

## Edit and preview

Requires Python 3.9+; no Python dependencies or frontend build tools are needed.

```sh
python3 scripts/build.py
python3 -m http.server 8000
```

- `data/publications.json`: curated titles, complete authors, venues, paper/code links, topic, and stable Scholar IDs. Preserve the ID when changing a title.
- `data/scholar.json`: the last verified citation snapshot, source links, and update timestamp.
- `templates/index.html`: biography, page structure, teaching, talks, and honors.
- `templates/logs.html`: the separate Logs page, linked from the top navigation and intentionally empty until the owner writes an entry.
- `stylesheet.css` and `assets/site.js`: responsive styling, accessible filters, and optional cached GitHub stars.
- `index.html` and `logs/index.html`: generated pages; rebuild after changing source data or templates.

The initial import on 27 October 2026 matched all 34 Scholar entries and added the 15 papers absent from the previous website. Existing author contribution markers and publication links were retained. Seven placeholder paper links were replaced with links verified on Scholar; the remaining GEMA-Score entry links to its Scholar record.

## Logs

The `/logs/` page contains no posts or sample content. When ready to publish writing, add it inside `#log-entries` in `templates/logs.html` and run the build. Citation refreshes only update Scholar data; they do not create log entries.

## Citation refresh

```sh
python3 scripts/update_scholar.py
python3 scripts/build.py
```

The updater makes ordinary requests to the public Scholar profile, follows pagination, and matches papers by Scholar ID. It does not use proxies, API keys, browser cookies, or CAPTCHA bypasses. A blocked request, changed markup, duplicate page, or missing curated paper makes the refresh fail before writing anything. The previously verified counts and their date remain visible. Citation counts may legitimately decrease when Scholar deduplicates articles.

A complete saved public profile can also be imported with `python3 scripts/update_scholar.py --html profile.html` after expanding all publications. New papers discovered during refresh are recorded in the snapshot; add their full metadata and topic to `data/publications.json` to display them.

## Deployment and schedule

The Website workflow validates pull requests, publishes `main` to GitHub Pages, and refreshes counts every Monday at 06:17 UTC. It can also be started manually in GitHub Actions. Successful refreshes commit the snapshot and generated HTML; the same run builds and deploys, since commits from the default Actions token do not trigger a separate Pages build. If refresh is blocked, a workflow warning and summary report it while the site continues using the cached data.

Set **Settings → Pages → Build and deployment → Source** to **GitHub Actions** when enabling this workflow. The existing site remains at https://huichizhou.github.io/ . The deployment artifact contains only the public HTML, CSS, assets, image, and data.

```sh
python3 -m unittest discover -s tests -v
node --check assets/site.js
```
