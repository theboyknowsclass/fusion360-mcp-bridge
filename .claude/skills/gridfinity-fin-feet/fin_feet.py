# Gridfinity fin feet: tapered loft + centre cut-out + outer bottom fillet.
#
# Select ONE planar face (parallel to XY, e.g. the underside of a baseplate)
# in Fusion, edit PARAMS below if needed, then run via fusion_execute.
#
# Result: the face is lofted DEPTH along its normal, the two short ends are
# angled in at ANGLE, a centred slot leaves two FIN_THICKNESS walls along the
# long sides, and the outer bottom edge of each fin is filleted.

import adsk.core, adsk.fusion, math

PARAMS = {
    "depth_mm": 50.0,          # how far the loft extends from the face
    "angle_deg": 45.0,         # taper angle of the short ends (from vertical)
    "fin_thickness_mm": 3.5,   # wall thickness of each fin
    "fillet_mm": 1.5,          # outer bottom fillet; steps down if it won't build
    "taper_axis": "auto",      # "auto" (taper along the long side), "x" or "y"
    "name": "Fin feet",        # prefix for created timeline items
}


def run(_context):
    p = PARAMS
    P = adsk.core.Point3D.create
    sel = ui.activeSelections
    if sel.count != 1 or not isinstance(sel.item(0).entity, adsk.fusion.BRepFace):
        print("Error: select exactly one face first")
        return
    face = sel.item(0).entity
    if not isinstance(face.geometry, adsk.core.Plane):
        print("Error: selected face is not planar")
        return
    ok, n = face.evaluator.getNormalAtPoint(face.pointOnFace)
    if abs(abs(n.z) - 1) > 1e-6:
        print("Error: face must be parallel to the XY plane")
        return

    body = face.body
    comp = body.parentComponent
    depth = p["depth_mm"] / 10
    inset = depth / math.tan(math.radians(p["angle_deg"]))
    fin = p["fin_thickness_mm"] / 10
    name = p["name"]

    bb = face.boundingBox
    xmin, ymin, xmax, ymax = bb.minPoint.x, bb.minPoint.y, bb.maxPoint.x, bb.maxPoint.y
    z0 = face.pointOnFace.z
    zb = z0 + n.z * depth

    # Corner radius from the face's outer-loop arcs (0 if square corners)
    r = 0.0
    for lp in face.loops:
        if lp.isOuter:
            for e in lp.edges:
                if isinstance(e.geometry, adsk.core.Arc3D):
                    r = max(r, e.geometry.radius)

    axis = p["taper_axis"]
    if axis == "auto":
        axis = "x" if (xmax - xmin) > (ymax - ymin) else "y"

    # u = taper axis, v = fin axis; map (u, v) back to model (x, y)
    if axis == "y":
        umin, umax, vmin, vmax = ymin, ymax, xmin, xmax
        to_xy = lambda u, v: (v, u)
    else:
        umin, umax, vmin, vmax = xmin, xmax, ymin, ymax
        to_xy = lambda u, v: (u, v)

    bottom_len = (umax - umin) - 2 * inset
    if bottom_len < 2 * r + 0.05:
        need = 2 * inset + 2 * r + 0.05
        print(f"Error: face is {(umax-umin)*10:.1f} mm along the taper axis; "
              f"needs at least {need*10:.1f} mm for {p['depth_mm']} mm at {p['angle_deg']} deg")
        return
    cut_w = (vmax - vmin) - 2 * fin
    if cut_w <= 0:
        print("Error: face too narrow for two fins of that thickness")
        return

    # 1. Top profile = the selected face
    sk1 = comp.sketches.add(face)
    sk1.project(face)
    sk1.name = f"{name} top profile"

    # 2. Bottom plane + rounded-rectangle bottom profile
    pin = comp.constructionPlanes.createInput()
    pin.setByOffset(face, adsk.core.ValueInput.createByReal(depth))
    pl = comp.constructionPlanes.add(pin)
    pl.name = f"{name} bottom plane"

    sk2 = comp.sketches.add(pl)
    sk2.name = f"{name} bottom profile"
    u0, u1 = umin + inset, umax - inset

    def S(u, v):
        x, y = to_xy(u, v)
        return sk2.modelToSketchSpace(P(x, y, zb))

    L = sk2.sketchCurves.sketchLines
    A = sk2.sketchCurves.sketchArcs
    if r > 0:
        k = r * (1 - 1 / math.sqrt(2))
        L.addByTwoPoints(S(u0 + r, vmin), S(u1 - r, vmin))
        L.addByTwoPoints(S(u1, vmin + r), S(u1, vmax - r))
        L.addByTwoPoints(S(u1 - r, vmax), S(u0 + r, vmax))
        L.addByTwoPoints(S(u0, vmax - r), S(u0, vmin + r))
        A.addByThreePoints(S(u1 - r, vmin), S(u1 - k, vmin + k), S(u1, vmin + r))
        A.addByThreePoints(S(u1, vmax - r), S(u1 - k, vmax - k), S(u1 - r, vmax))
        A.addByThreePoints(S(u0 + r, vmax), S(u0 + k, vmax - k), S(u0, vmax - r))
        A.addByThreePoints(S(u0, vmin + r), S(u0 + k, vmin + k), S(u0 + r, vmin))
    else:
        L.addTwoPointRectangle(S(u0, vmin), S(u1, vmax))
    if sk1.profiles.count == 0 or sk2.profiles.count == 0:
        print(f"Error: profile not formed (top {sk1.profiles.count}, bottom {sk2.profiles.count})")
        return

    # 3. Loft, joined to the selected body
    li = comp.features.loftFeatures.createInput(adsk.fusion.FeatureOperations.JoinFeatureOperation)
    li.loftSections.add(sk1.profiles.item(0))
    li.loftSections.add(sk2.profiles.item(0))
    li.isSolid = True
    li.participantBodies = [body]
    loft = comp.features.loftFeatures.add(li)
    loft.name = f"{name} loft"

    # 4. Centred slot -> two fins (symmetric so direction doesn't matter;
    #    the far side lies in empty space below the bottom plane)
    sk3 = comp.sketches.add(pl)
    sk3.name = f"{name} cutout"
    vc = (vmin + vmax) / 2
    a = to_xy(umin - 1, vc - cut_w / 2)
    b = to_xy(umax + 1, vc + cut_w / 2)
    sk3.sketchCurves.sketchLines.addTwoPointRectangle(
        sk3.modelToSketchSpace(P(a[0], a[1], zb)),
        sk3.modelToSketchSpace(P(b[0], b[1], zb)))
    ei = comp.features.extrudeFeatures.createInput(
        sk3.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.setSymmetricExtent(adsk.core.ValueInput.createByReal(depth), False)
    ei.participantBodies = [body]
    cut = comp.features.extrudeFeatures.add(ei)
    cut.name = f"{name} cut"

    # 5. Fillet the outer bottom edge of each fin (skip inner slot edges)
    inner_v = (vc - cut_w / 2, vc + cut_w / 2)
    edges = adsk.core.ObjectCollection.create()
    for f in body.faces:
        fb = f.boundingBox
        if abs(fb.minPoint.z - zb) > 1e-4 or abs(fb.maxPoint.z - zb) > 1e-4:
            continue
        for e in f.edges:
            if e.length < 1.0:
                continue
            eb = e.boundingBox
            lo = eb.minPoint.y if axis == "x" else eb.minPoint.x
            hi = eb.maxPoint.y if axis == "x" else eb.maxPoint.x
            if any(abs(lo - iv) < 1e-4 and abs(hi - iv) < 1e-4 for iv in inner_v):
                continue
            edges.add(e)

    fillet_used = None
    rr = p["fillet_mm"]
    while edges.count and rr >= 0.25:
        try:
            fi = comp.features.filletFeatures.createInput()
            fi.edgeSetInputs.addConstantRadiusEdgeSet(
                edges, adsk.core.ValueInput.createByString(f"{rr} mm"), True)
            fil = comp.features.filletFeatures.add(fi)
            if fil.healthState == 0:
                fil.name = f"{name} fillet"
                fillet_used = rr
                break
            fil.deleteMe()
        except Exception:
            pass
        rr = round(rr - 0.25, 2)

    print(f"Done on '{body.name}': taper axis {axis.upper()}, "
          f"top {(umax-umin)*10:.1f} mm -> bottom {bottom_len*10:.1f} mm, "
          f"slot {cut_w*10:.1f} mm, fins {p['fin_thickness_mm']} mm, "
          f"corner r {r*10:.2f} mm, outer edges {edges.count}, "
          f"fillet {fillet_used if fillet_used is not None else 'FAILED (removed)'} mm")
