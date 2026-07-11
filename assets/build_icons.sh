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

# 1b) Monochrome menu-bar glyphs, from the hi-res tiles BEFORE they are downscaled.
#     A FILLED dumbbell (bold + clearly visible next to system icons) with the
#     structural lines (outer outline, plate divisions, handle) cut out as thin
#     see-through gaps via Canny edges — so it reads as a solid dumbbell WITH detail,
#     not a featureless blob. Black + alpha -> macOS renders it as an adaptive
#     template (white on a dark bar, black on light). 32px @144dpi = 16pt.
#     template = clean dumbbell (busy shape s_2); template_error = cracked (s_5).
_glyph() {  # $1 = source tile, $2 = output
  local sil edges WH; sil=$(mktemp).png; edges=$(mktemp).png
  WH=$(magick identify -format "%wx%h" "$1")
  # silhouette alpha = full dumbbell footprint (key only the OUTER white)
  magick "$1" -alpha set -bordercolor white -border 1 -fuzz 15% -fill none \
    -draw "alpha 0,0 floodfill" -shave 1x1 +repage -alpha extract "$sil"
  # structural lines, thickened, then inverted so lines become the cut-out gaps
  magick "$1" -background white -flatten -colorspace Gray -canny 0x1+10%+30% \
    -morphology Dilate Disk:2 -negate "$edges"
  # final alpha = silhouette AND NOT(lines); paint it solid black; size to 16pt
  magick "$sil" "$edges" -compose multiply -composite \
    \( -size "$WH" xc:black \) +swap -alpha off -compose CopyOpacity -composite \
    -trim +repage -filter Lanczos -resize x32 -units PixelsPerInch -density 144 "$2"
  rm -f "$sil" "$edges"
}
_glyph "$OUT/s_2.png" "$OUT/template.png"
_glyph "$OUT/s_5.png" "$OUT/template_error.png"

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

echo "Built: $OUT/{quiet,moderate,busy,nodata,error}.png (color, 18pt) + template{,_error}.png (filled glyph, 16pt)"
