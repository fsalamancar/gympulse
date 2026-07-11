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

# 1b) Monochrome GAUGE glyphs for the menu bar, from the hi-res tiles BEFORE they
#     are downscaled. The dumbbell is a transparent OUTLINE that FILLS HORIZONTALLY
#     from the left in proportion to how busy the gym is (0% = empty outline,
#     100% = solid) — the original gauge idea. Black + alpha, so macOS renders it as
#     an adaptive template icon (white on a dark bar, black on light). 32px @144dpi
#     = 16pt. fill_0..fill_100 = the levels; template_error = cracked outline (s_5).
TILE="$OUT/s_2.png"                 # busy tile = full symmetric dumbbell shape
SIL=$(mktemp).png; OUTL=$(mktemp).png
# silhouette footprint (key only the OUTER white), sized to final 16pt
magick "$TILE" -alpha set -bordercolor white -border 1 -fuzz 15% -fill none \
  -draw "alpha 0,0 floodfill" -shave 1x1 +repage -alpha extract \
  -filter Lanczos -resize x32 "$SIL"
# outline (structural lines), slightly thickened so the empty gauge stays visible
magick "$TILE" -background white -flatten -colorspace Gray -canny 0x1+10%+30% \
  -morphology Dilate Disk:1.5 -filter Lanczos -resize x32 "$OUTL"
GW=$(magick identify -format "%w" "$SIL"); GH=$(magick identify -format "%h" "$SIL")
LMASK=$(mktemp).png
for p in 0 10 20 30 40 50 60 70 80 90 100; do
  x=$(( GW * p / 100 ))
  # left-fill mask: white columns 0..x (nothing at 0%)
  if [ "$x" -gt 0 ]; then
    magick -size "${GW}x${GH}" xc:black -fill white -draw "rectangle 0,0 $((x-1)),$((GH-1))" "$LMASK"
  else
    magick -size "${GW}x${GH}" xc:black "$LMASK"
  fi
  # final alpha = outline OR (silhouette AND left-of-x); paint black; tag 144dpi
  magick "$SIL" "$LMASK" -compose multiply -composite \
    "$OUTL" -compose Lighten -composite \
    \( -size "${GW}x${GH}" xc:black \) +swap -alpha off -compose CopyOpacity -composite \
    -units PixelsPerInch -density 144 "$OUT/fill_${p}.png"
done
rm -f "$SIL" "$OUTL" "$LMASK"
# Error glyph: cracked dumbbell as a bold outline (from s_5), same 16pt template.
magick "$OUT/s_5.png" -background white -flatten -colorspace Gray -canny 0x1+10%+30% \
  -morphology Dilate Disk:2 \( +clone \) -alpha off -compose CopyOpacity -composite \
  -channel RGB -evaluate set 0 +channel -trim +repage \
  -filter Lanczos -resize x32 -units PixelsPerInch -density 144 "$OUT/template_error.png"

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

echo "Built: $OUT/{quiet,moderate,busy,nodata,error}.png (color, 18pt) + fill_0..100.png gauge + template_error.png (16pt)"
