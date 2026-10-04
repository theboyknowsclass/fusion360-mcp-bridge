---
name: gridfinity-fin-feet
description: Add tapered "fin" feet under a Gridfinity baseplate (or any rounded-rectangle face) in Fusion 360 — loft the selected face down with the short ends angled in, cut a centred slot to leave two fins, and fillet the fins' outer bottom edges. Use when the user asks for fin feet, tapered feet/legs, or to repeat the baseplate fin routine on another plate.
---

# Gridfinity fin feet

Runs [fin_feet.py](fin_feet.py) through `fusion_execute` against the face the user has selected in Fusion.

## Steps

1. Confirm the user has selected **one planar face parallel to XY** (normally the underside of the plate). If unsure, probe `ui.activeSelections` and print the face's bounding box, normal and body name.
2. Read `fin_feet.py`. Edit the `PARAMS` dict only if the user asked for different values:
   - `depth_mm` (default 50), `angle_deg` (45), `fin_thickness_mm` (3.5),
     `fillet_mm` (1.5, steps down by 0.25 mm until it builds), `taper_axis` ("auto" = taper the long direction), `name`.
3. Pass the full file contents as the `script` argument to `fusion_execute`.
4. Report the printed summary line, then verify with `fusion_screenshot` (a side view along the fins shows the taper).

## Size limits

The face must be longer than `2 × depth / tan(angle) + 2 × corner radius` along the taper axis.
At the defaults (50 mm, 45°, 3.25 mm Gridfinity corners) that is about **107 mm**, so:

| Gridfinity units along taper | Face length | Flat foot |
|---|---|---|
| 2 | ~82.5 mm | impossible |
| 3 | ~124.5 mm | ~24.5 mm |
| 4 | ~166.5 mm | ~66.5 mm |
| 5 | 208.5 mm | 108.5 mm |

The script refuses with the required length if the face is too short. For short plates suggest a shallower depth or steeper angle (e.g. 30 mm at 45° needs ~67 mm).

## Notes

- The fillet tops out around 1.25–1.5 mm (1.5 on a 5×2, 1.25 on a 3×2) with 3.5 mm fins and 3.25 mm corners: the corner round leaves a ~0.25 mm sliver at each fin end that larger fillets can't wrap around.
- All created items are prefixed with `name` in the timeline (top/bottom profile sketches, bottom plane, loft, cutout sketch, cut, fillet), so depth/angle can be edited afterwards via the bottom plane offset and bottom sketch.
