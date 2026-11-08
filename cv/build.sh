#!/usr/bin/env bash
# Print cv/cv.html to public/cv.pdf with a headless Chromium-based browser.
# Usage: cv/build.sh            (or set CHROME=/path/to/browser)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
src="$here/cv.html"
out="$here/../public/cv.pdf"

find_browser() {
  if [[ -n "${CHROME:-}" ]]; then echo "$CHROME"; return 0; fi
  local candidates=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
  )
  local c
  for c in "${candidates[@]}"; do [[ -x "$c" ]] && { echo "$c"; return 0; }; done
  # Playwright's Chromium (npx playwright install chromium) also works.
  for c in "$HOME"/Library/Caches/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium \
           "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux/chrome; do
    [[ -x "$c" ]] && { echo "$c"; return 0; }
  done
  for c in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge; do
    command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return 0; }
  done
  return 1
}

if ! browser="$(find_browser)"; then
  echo "No Chrome, Chromium or Edge found (set CHROME=/path/to/browser)." >&2
  echo "Fallback: open cv/cv.html in a browser → Print → Save as PDF (A4, no headers/footers, margins: default) → public/cv.pdf" >&2
  exit 1
fi

mkdir -p "$(dirname "$out")"
# --virtual-time-budget gives the Inter web font time to load before printing.
"$browser" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=10000 --run-all-compositor-stages-before-draw \
  --print-to-pdf="$out" "file://$src" 2>/dev/null

if [[ -s "$out" ]]; then
  echo "Wrote $out"
else
  echo "Printing failed. Fallback: open cv/cv.html in a browser → Print → Save as PDF → public/cv.pdf" >&2
  exit 1
fi
