# CV

`cv.html` is the source of the downloadable CV served at `/cv.pdf` (`public/cv.pdf`).

1. Edit the text in `cv/cv.html`. It's plain HTML: one `<div class="entry">` per job, project or award.
2. Rebuild the PDF: run `cv/build.sh` from the repo root. It uses headless Chrome, Chromium or Edge or Playwright's Chromium (`npx playwright install chromium`); override with `CHROME=/path/to/browser`.
3. No browser found? Open `cv/cv.html` in a browser → Print → Save as PDF (A4, no headers/footers) → `public/cv.pdf`.
4. Keep it to 2 pages, and keep text as real text (no images) so ATS parsers can read it.
5. When the portfolio domain is live, uncomment the portfolio line in the header.
