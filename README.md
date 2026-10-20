# Federal Reserve Research Hub

A self-updating, searchable page that gathers the latest working papers, economic
research, blogs, and news/press from all twelve regional Federal Reserve Banks and
the Board of Governors — grouped by bank, with research listed first.

**Live site:** published via GitHub Pages (see the repo's Pages settings for the URL).

## How it works

- [`refresh_fed_hub.py`](refresh_fed_hub.py) pulls titles, dates, and links from
  official Federal Reserve RSS feeds (Board of Governors, New York, Richmond, Atlanta)
  and the [RePEc/IDEAS](https://ideas.repec.org) research index (working-paper series
  for the banks whose sites don't publish a feed). It injects the results into
  [`template.html`](template.html) and writes `fed-research-hub.html`.
- The GitHub Actions workflow [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml)
  runs the script **every Monday at 13:00 UTC** (8am US Central during daylight time),
  rebuilds the page, and deploys it to GitHub Pages. You can also trigger it any time
  from the **Actions** tab ("Run workflow").

## Run it locally

```bash
python refresh_fed_hub.py
# open fed-research-hub.html in a browser
```

## Notes

- GitHub disables scheduled workflows after 60 days with no repository activity; the
  weekly deploy commit keeps it active, but if it ever pauses, open the Actions tab and
  run it once to re-arm it.
- Not affiliated with the Federal Reserve. Links open each bank's official site.
