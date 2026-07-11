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

# 3) Resize for a retina menu bar (~36px tall @2x), keep pixels crisp, 2:1 dumbbell.
for f in "$OUT"/s_*.png; do
  magick "$f" -filter point -resize x36 "$f"
done

# 4) Name by state (top row: green/amber/red ; bottom row: red-alt/grey/cracked).
mv "$OUT/s_0.png" "$OUT/quiet.png"
mv "$OUT/s_1.png" "$OUT/moderate.png"
mv "$OUT/s_2.png" "$OUT/busy.png"
mv "$OUT/s_4.png" "$OUT/nodata.png"
mv "$OUT/s_5.png" "$OUT/error.png"
rm -f "$OUT/s_3.png"   # spare red
echo "Built: $OUT/{quiet,moderate,busy,nodata,error}.png"
