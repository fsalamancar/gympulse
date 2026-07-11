#!/usr/bin/env bash
# One-time: slice the 3x2 sprite sheet into transparent, retina-sized state icons.
# Requires: imagemagick (brew install imagemagick).
set -euo pipefail
cd "$(dirname "$0")"

SHEET="gympulse-icons-sheet.png"
OUT="icons"
mkdir -p "$OUT"

# 1) Slice into 6 tiles s_0..s_5 (3 cols x 2 rows).
magick "$SHEET" -crop 3x2@ +repage "$OUT/s_%d.png"

# 2) Key out the white background to transparency (flood-fill from the corner so
#    only the OUTER white becomes transparent — white pixels inside a dumbbell,
#    if any, are preserved). Low fuzz keeps the grey metal/outlines intact.
for f in "$OUT"/s_*.png; do
  magick "$f" -alpha set -bordercolor white -border 1 \
    -fuzz 15% -fill none -draw "alpha 0,0 floodfill" \
    -shave 1x1 -trim +repage "$f"
done

# 3) Size for the menu bar. We keep 36 physical px of detail but tag the PNG at
#    144 DPI (2x) so macOS/SwiftBar renders it at 18pt tall — crisp on retina AND
#    the right size next to the ~18pt system menu-bar icons (not the huge ~36pt
#    a 72-DPI 36px image would be). Smooth filter downscales the hi-res tile cleanly.
for f in "$OUT"/s_*.png; do
  magick "$f" -resize x36 -units PixelsPerInch -density 144 "$f"
done

# 4) Name by state (top row: green/amber/red ; bottom row: red-alt/grey/cracked).
mv "$OUT/s_0.png" "$OUT/quiet.png"
mv "$OUT/s_1.png" "$OUT/moderate.png"
mv "$OUT/s_2.png" "$OUT/busy.png"
mv "$OUT/s_4.png" "$OUT/nodata.png"
mv "$OUT/s_5.png" "$OUT/error.png"
rm -f "$OUT/s_3.png"   # spare red

# 5) Monochrome menu-bar glyphs (black content + alpha). macOS renders template
#    images adapting to light/dark, so these match the system menu-bar icons.
#    Smaller (32px @144dpi = 16pt). template = clean dumbbell, template_error = cracked.
magick "$OUT/busy.png"  -channel RGB -evaluate set 0 +channel \
  -resize x32 -units PixelsPerInch -density 144 "$OUT/template.png"
magick "$OUT/error.png" -channel RGB -evaluate set 0 +channel \
  -resize x32 -units PixelsPerInch -density 144 "$OUT/template_error.png"

echo "Built: $OUT/{quiet,moderate,busy,nodata,error}.png + template{,_error}.png (monochrome, 16pt)"
