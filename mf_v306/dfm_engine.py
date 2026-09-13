"""
MechForge AI V2 - Transparent DFM rules engine.
This is a decision-support prototype, not a certification or supplier quote.
"""

PROCESS_OPTIONS = [
    "AUTO SELECT", "CNC Milling", "CNC Turning", "Drilling", "Grinding",
    "Sheet Metal", "Laser Cutting", "Waterjet Cutting", "Casting", "Forging",
    "Injection Molding", "3D Printing", "Welding",
]

MATERIAL_FACTORS = {
    "Aluminium 6061": 1.00,
    "Aluminium 7075": 1.20,
    "Mild Steel": 1.10,
    "Stainless Steel": 1.50,
    "Cast Iron": 1.20,
    "Brass": 1.35,
    "Copper": 1.45,
    "Titanium": 3.00,
    "Engineering Plastic": 0.90,
}


def clamp(value, low=0, high=100):
    return max(low, min(high, float(value)))


def _issue(priority, title, observed, problem, recommendation, benefit):
    return dict(
        priority=priority, title=title, observed=observed,
        problem=problem, recommendation=recommendation, benefit=benefit
    )


def choose_process(d):
    requested = d.get("process", "AUTO SELECT")
    if requested != "AUTO SELECT":
        return requested, 90, [
            f"{requested} was selected by the user",
            f"{d['material']} is included in the material assessment",
            f"Quantity of {int(d['quantity']):,} is included in the economic assessment",
        ], "Review alternative processes if production volume changes."

    # Transparent prototype logic.
    quantity = d["quantity"]
    if d["pocket_depth"] > 0 or d["radius"] > 0 or d["hole_dia"] > 0:
        if quantity >= 500 and d["material"] == "Aluminium 6061":
            return "CNC Milling", 92, [
                "Pocket/radius/hole geometry is compatible with machining",
                "Aluminium 6061 has good general machinability",
                f"Quantity of {int(quantity):,} supports a repeatable machining process",
                "Tolerance and surface finish are included in the DFM checks",
            ], "Die Casting — consider at high volume after tooling economics are justified."
        return "CNC Milling", 92, [
            "Pocket/radius/hole geometry is compatible with CNC machining",
            f"{d['material']} is included in the material assessment",
            f"Quantity of {int(quantity):,} influences economic suitability",
            "Tolerance and surface-finish requirements are included in the DFM checks",
        ], "Die Casting — consider for higher volumes when tooling economics support it."

    return "CNC Milling", 78, [
        "CNC Milling is a versatile default for prismatic components",
        f"{d['material']} is included in the material assessment",
        f"Quantity of {int(quantity):,} influences economic suitability",
    ], "Review turning, sheet metal or additive processes if the geometry requires them."


def analyze_design(d):
    issues = []

    wall = float(d["wall"])
    radius = float(d["radius"])
    pocket_depth = float(d["pocket_depth"])
    pocket_width = max(float(d["pocket_width"]), 0.1)
    hole_dia = float(d["hole_dia"])
    hole_depth = float(d["hole_depth"])
    tolerance = float(d["tolerance"])
    surface_ra = float(d["surface_ra"])
    material = d["material"]

    # Individual category scores start at 100 and are reduced by explicit rules.
    geometry = 100.0
    machinability = 100.0
    tolerance_score = 100.0
    accessibility = 100.0
    material_score = 92.0
    cost_score = 100.0

    if radius <= 0:
        issues.append(_issue(
            "HIGH", "Sharp internal corner", "Internal radius = 0 mm",
            "A conventional milling cutter cannot create a perfectly sharp internal corner.",
            "Add an internal radius appropriate to the cutter and functional requirement.",
            "Simpler tooling and lower machining time."
        ))
        geometry -= 15
        accessibility -= 12
    elif radius < 2:
        issues.append(_issue(
            "MEDIUM", "Small internal radius", f"{radius:g} mm",
            "Small radii can require smaller tools and increase machining time.",
            "Increase the radius where functionally acceptable.",
            "Larger cutter and improved productivity."
        ))
        geometry -= 7
        accessibility -= 6
    else:
        issues.append(_issue(
            "GOOD", "Reasonable internal radius", f"{radius:g} mm",
            "No major radius issue was detected by the current prototype rule.",
            "Retain unless the functional requirement requires another value.",
            "Good conventional machining accessibility."
        ))

    ratio = pocket_depth / pocket_width
    if ratio > 4:
        issues.append(_issue(
            "HIGH", "Deep/narrow pocket", f"{pocket_depth:g} × {pocket_width:g} mm ({ratio:.1f}:1)",
            "High depth-to-width ratio can require long-reach tooling and reduce rigidity.",
            "Widen the pocket or reduce depth if functionally possible.",
            "Lower tool deflection and machining risk."
        ))
        geometry -= 12
        machinability -= 10
        accessibility -= 12
    elif ratio > 2:
        issues.append(_issue(
            "MEDIUM", "Moderately deep pocket", f"Depth/width ratio = {ratio:.1f}:1",
            "Longer tools may be required for the pocket.",
            "Review tool reach and consider a wider pocket.",
            "Improved rigidity and cycle time."
        ))
        geometry -= 5
        machinability -= 5
        accessibility -= 6

    if wall < 2:
        issues.append(_issue(
            "HIGH", "Thin wall", f"{wall:g} mm",
            "Very thin walls can deflect or vibrate during machining.",
            "Increase wall thickness where structural requirements permit.",
            "Better rigidity and dimensional stability."
        ))
        geometry -= 12
        machinability -= 8
    elif wall < 3:
        issues.append(_issue(
            "MEDIUM", "Relatively thin wall", f"{wall:g} mm",
            "Thin sections can be more sensitive to deflection and heat.",
            "Review rigidity and workholding; increase thickness if practical.",
            "More stable machining."
        ))
        geometry -= 5
        machinability -= 4
    else:
        issues.append(_issue(
            "GOOD", "Adequate wall thickness", f"{wall:g} mm",
            "No thin-wall issue was triggered by the current prototype rule.",
            "Retain the wall thickness unless structural requirements indicate otherwise.",
            "Good general machining rigidity."
        ))

    if hole_dia > 0 and hole_depth / max(hole_dia, 0.1) > 5:
        ratio_h = hole_depth / hole_dia
        issues.append(_issue(
            "MEDIUM", "Deep hole", f"{hole_depth:g} mm / Ø{hole_dia:g} mm ({ratio_h:.1f}×D)",
            "Deep drilling increases chip-evacuation and tool-breakage risk.",
            "Review peck drilling, access and hole depth.",
            "Improved drilling reliability."
        ))
        machinability -= 6
        accessibility -= 5
    else:
        issues.append(_issue(
            "GOOD", "Reasonable hole depth", f"{hole_depth:g} mm / Ø{hole_dia:g} mm",
            "The current prototype rule did not flag the hole depth.",
            "Retain unless the selected drill/process requires another approach.",
            "Standard drilling strategy is more likely to be practical."
        ))

    if tolerance <= 0.01:
        issues.append(_issue(
            "HIGH", "Very tight tolerance", f"±{tolerance:.3f} mm",
            "Very tight tolerances may require precision machining, controlled inspection or grinding.",
            "Apply the tight tolerance only where function requires it.",
            "Potentially significant cost reduction."
        ))
        tolerance_score -= 15
        cost_score -= 12
    elif tolerance < 0.03:
        issues.append(_issue(
            "MEDIUM", "Tight tolerance", f"±{tolerance:.3f} mm",
            "Tighter tolerances generally increase inspection and process-control requirements.",
            "Confirm that this tolerance is functionally necessary.",
            "Reduced inspection and machining cost."
        ))
        tolerance_score -= 7
        cost_score -= 6
    else:
        issues.append(_issue(
            "GOOD", "Reasonable tolerance", f"±{tolerance:.3f} mm",
            "No tight-tolerance warning was triggered by the current prototype rule.",
            "Retain the tolerance if it satisfies the functional requirement.",
            "Avoids unnecessary precision-machining requirements."
        ))

    if surface_ra < 0.8:
        issues.append(_issue(
            "MEDIUM", "Fine surface finish", f"Ra {surface_ra:g} µm",
            "Very fine finish can require additional finishing operations.",
            "Confirm that the finish is functionally necessary.",
            "Avoid unnecessary finishing cost."
        ))
        machinability -= 5
        cost_score -= 7
    else:
        issues.append(_issue(
            "GOOD", "Machinable surface finish", f"Ra {surface_ra:g} µm",
            "No fine-finish warning was triggered by the current prototype rule.",
            "Retain the specified finish where functionally required.",
            "Lower risk of unnecessary finishing operations."
        ))

    # Material score is intentionally modest: machinability is not the same as suitability.
    if material == "Titanium":
        material_score = 72
        machinability -= 10
    elif material == "Stainless Steel":
        material_score = 84
        machinability -= 5
    elif material == "Engineering Plastic":
        material_score = 94
    elif material in {"Aluminium 6061", "Aluminium 7075"}:
        material_score = 95
    else:
        material_score = 90

    geometry = clamp(geometry)
    machinability = clamp(machinability)
    tolerance_score = clamp(tolerance_score)
    accessibility = clamp(accessibility)
    material_score = clamp(material_score)
    cost_score = clamp(cost_score)

    # Weighted overall score.
    score = round(
        geometry * 0.22
        + machinability * 0.22
        + tolerance_score * 0.16
        + accessibility * 0.16
        + material_score * 0.12
        + cost_score * 0.12
    )
    score = int(clamp(score))

    recommended, confidence, reasons, alternative = choose_process(d)

    # Transparent prototype cost model.
    complexity = (100 - score) / 100
    base = 450.0
    factor = MATERIAL_FACTORS.get(material, 1.2)
    quantity = max(1, int(d["quantity"]))
    unit = base * factor * (1 + 0.80 * complexity)

    # Very tight tolerances / fine finishes also affect cycle and setup cost.
    if tolerance < 0.03:
        unit *= 1.10
    if surface_ra < 0.8:
        unit *= 1.08

    minutes = 10 + complexity * 22
    if ratio > 4:
        minutes += 3
    if hole_dia > 0 and hole_depth / max(hole_dia, 0.1) > 5:
        minutes += 2

    low = unit * 0.85
    high = unit * 1.20

    classification = (
        "Excellent" if score >= 90 else
        "Good" if score >= 75 else
        "Needs Improvement" if score >= 50 else
        "Difficult to Manufacture"
    )

    # Avoid impossible >100 display values.
    breakdown = {
        "Geometry": int(round(geometry)),
        "Machinability": int(round(machinability)),
        "Tolerance": int(round(tolerance_score)),
        "Tool Accessibility": int(round(accessibility)),
        "Material": int(round(material_score)),
        "Cost Efficiency": int(round(cost_score)),
    }

    # Build the result safely. Do not use dict(**d, score=...) because d may
    # already contain keys such as score when analyze_design() is called on a
    # previous analysis result (for example from the What-If simulator).
    result = dict(d)
    result.update({
        "score": score,
        "classification": classification,
        "breakdown": breakdown,
        "issues": issues,
        "recommended_process": recommended,
        "confidence": confidence,
        "reasons": reasons,
        "alternative": alternative,
        "unit_low": low,
        "unit_high": high,
        "batch_low": low * quantity,
        "batch_high": high * quantity,
        "minutes": minutes,
    })
    return result


PROCESS_COMPARISON_PROFILES = {
    "CNC Milling": {"base": 100, "geometry": 0, "material": 0, "volume": 0, "speed": 1.00, "setup": 0.0},
    "CNC Turning": {"base": 62, "geometry": -24, "material": 0, "volume": 2, "speed": 0.82, "setup": 2.0},
    "Drilling": {"base": 70, "geometry": -18, "material": 0, "volume": 1, "speed": 0.70, "setup": 1.0},
    "Grinding": {"base": 58, "geometry": -20, "material": 0, "volume": -1, "speed": 0.55, "setup": 3.0},
    "Sheet Metal": {"base": 48, "geometry": -28, "material": -5, "volume": 4, "speed": 0.42, "setup": 1.5},
    "Laser Cutting": {"base": 45, "geometry": -30, "material": -2, "volume": 5, "speed": 0.35, "setup": 1.0},
    "Waterjet Cutting": {"base": 54, "geometry": -24, "material": 2, "volume": 3, "speed": 0.50, "setup": 1.5},
    "Casting": {"base": 52, "geometry": -8, "material": 0, "volume": 8, "speed": 0.30, "setup": 4.0},
    "Forging": {"base": 45, "geometry": -16, "material": -3, "volume": 7, "speed": 0.34, "setup": 4.5},
    "Injection Molding": {"base": 35, "geometry": -18, "material": 0, "volume": 10, "speed": 0.22, "setup": 5.0},
    "3D Printing": {"base": 66, "geometry": -2, "material": 4, "volume": -3, "speed": 1.65, "setup": 0.5},
    "Welding": {"base": 42, "geometry": -20, "material": -4, "volume": 2, "speed": 0.75, "setup": 2.5},
}


def compare_processes(d):
    """Compare plausible manufacturing routes using transparent prototype rules.

    The comparison is a decision-support estimate, not a supplier quote. Each
    process receives a suitability score based on the same design inputs plus
    process-specific geometry, material, volume and finishing heuristics.
    """
    quantity = max(1, int(d["quantity"]))
    material = d["material"]
    radius = float(d["radius"])
    wall = float(d["wall"])
    pocket_depth = float(d["pocket_depth"])
    pocket_width = max(float(d["pocket_width"]), 0.1)
    hole_dia = float(d["hole_dia"])
    hole_depth = float(d["hole_depth"])
    tolerance = float(d["tolerance"])
    surface_ra = float(d["surface_ra"])
    pocket_ratio = pocket_depth / pocket_width
    hole_ratio = hole_depth / max(hole_dia, 0.1) if hole_dia > 0 else 0

    base_analysis = analyze_design(d)
    rows = []
    for process, profile in PROCESS_COMPARISON_PROFILES.items():
        score = float(profile["base"])
        reasons = []
        risks = []

        # Geometry suitability.
        if process == "CNC Milling":
            if pocket_depth > 0 or radius > 0 or hole_dia > 0:
                score += 5
                reasons.append("Pocket, radius and hole features are directly machinable")
            if pocket_ratio > 4:
                score -= 8
                risks.append("Deep/narrow pocket increases long-reach tooling risk")
            if radius < 2:
                score -= 5
                risks.append("Small internal radius may need smaller tooling")
        elif process == "CNC Turning":
            if pocket_depth > 0 or pocket_width > 0:
                score -= 18
                risks.append("Prismatic pocket geometry is not a natural turning feature")
            if hole_dia > 0:
                score += 3
                reasons.append("Axial holes can be drilled on a lathe")
        elif process == "Drilling":
            if hole_dia > 0:
                score += 10
                reasons.append("Hole feature is directly suited to drilling")
            if pocket_depth > 0 or radius > 0:
                score -= 22
                risks.append("Drilling alone cannot produce the complete pocket/radius geometry")
        elif process == "Grinding":
            if tolerance <= 0.02:
                score += 8
                reasons.append("Precision tolerance can benefit from grinding capability")
            if surface_ra <= 1.6:
                score += 8
                reasons.append("Fine surface finish is compatible with grinding")
            if pocket_depth > 0:
                score -= 16
                risks.append("Pocketed geometry is difficult to grind directly")
        elif process in {"Sheet Metal", "Laser Cutting", "Waterjet Cutting"}:
            if pocket_depth > 0 or radius > 0:
                score -= 16
                risks.append("3D pocket/radius geometry is not naturally produced from flat sheet")
            if wall <= 6:
                score += 5
                reasons.append("Thin-section geometry is favorable for sheet-based processes")
            else:
                score -= 8
        elif process == "Casting":
            if pocket_depth > 0:
                score += 4
                reasons.append("Complex pockets can be formed with appropriate tooling/core design")
            if tolerance < 0.05:
                score -= 10
                risks.append("Tight tolerances may require machining after casting")
            if surface_ra < 1.6:
                score -= 8
                risks.append("Fine surface finish may require secondary finishing")
        elif process == "Forging":
            if wall >= 3:
                score += 3
                reasons.append("Robust sections can suit forged preforms")
            if pocket_depth > 0:
                score -= 12
                risks.append("Deep pockets generally need substantial secondary machining")
        elif process == "Injection Molding":
            if material == "Engineering Plastic":
                score += 15
                reasons.append("Material is compatible with injection molding")
            else:
                score -= 20
                risks.append("Selected material is not a conventional injection-molding feedstock")
            if quantity < 500:
                score -= 18
                risks.append("Tooling cost is difficult to justify at this volume")
        elif process == "3D Printing":
            if pocket_depth > 0 or complex_feature_count(d) > 0:
                score += 8
                reasons.append("Additive manufacturing handles internal/complex geometry well")
            if tolerance < 0.05:
                score -= 10
                risks.append("Tight tolerance may require post-processing")
            if surface_ra < 1.6:
                score -= 8
                risks.append("Fine surface finish may need post-processing")
        elif process == "Welding":
            score -= 10
            risks.append("Welding is better suited to fabricated assemblies than a single machined bracket")

        # Material suitability.
        if material == "Titanium" and process in {"CNC Milling", "Grinding"}:
            score += 3
        if material == "Engineering Plastic" and process == "3D Printing":
            score += 5
        if material in {"Aluminium 6061", "Aluminium 7075"} and process == "CNC Milling":
            score += 4
            reasons.append("Aluminium is well suited to conventional CNC machining")

        # Volume economics: additive/one-off processes are less attractive at
        # high volume; tooling-heavy processes become more attractive as volume rises.
        if quantity >= 500 and process in {"Casting", "Forging", "Injection Molding"}:
            score += profile["volume"]
            reasons.append("Higher volume improves tooling economics")
        elif quantity < 100 and process in {"Casting", "Forging", "Injection Molding"}:
            score -= 12
            risks.append("Low production volume weakens tooling economics")
        elif quantity >= 500 and process == "3D Printing":
            score -= 10
            risks.append("High volume generally favors faster conventional production routes")

        # Process-specific tolerance/finish sensitivity.
        if tolerance <= 0.01 and process in {"Laser Cutting", "Waterjet Cutting", "Casting", "Forging", "3D Printing"}:
            score -= 5
        if surface_ra <= 0.8 and process in {"Laser Cutting", "Waterjet Cutting", "3D Printing", "Casting"}:
            score -= 5

        # Keep the comparison baseline consistent with the main DFM result.
        # Other processes are screened against the same design, while CNC Milling
        # represents the currently analyzed route directly.
        if process == "CNC Milling":
            score = int(base_analysis["score"])
        else:
            score = int(round(clamp(score, 0, 100)))

        # Transparent relative cost/time estimate. CNC baseline comes from the
        # main DFM model; other processes are scaled heuristically for comparison.
        cnc_unit = base_analysis["unit_low"]
        cnc_minutes = base_analysis["minutes"]
        cost_factor = {
            "CNC Milling": 1.00, "CNC Turning": 0.88, "Drilling": 0.55,
            "Grinding": 1.25, "Sheet Metal": 0.72, "Laser Cutting": 0.62,
            "Waterjet Cutting": 0.90, "Casting": 0.50, "Forging": 0.65,
            "Injection Molding": 0.35, "3D Printing": 1.35, "Welding": 0.95,
        }[process]
        volume_factor = 1.0
        if quantity >= 500 and process in {"Casting", "Forging", "Injection Molding"}:
            volume_factor = 0.70
        if quantity < 100 and process in {"Casting", "Forging", "Injection Molding"}:
            volume_factor = 1.80
        if process == "CNC Milling":
            estimated_unit = base_analysis["unit_low"]
            estimated_low = base_analysis["unit_low"]
            estimated_high = base_analysis["unit_high"]
        else:
            estimated_unit = cnc_unit * cost_factor * volume_factor * (1 + max(0, 90 - score) / 500)
            estimated_low = estimated_unit * 0.85
            estimated_high = estimated_unit * 1.20
        estimated_time = max(2.0, cnc_minutes * profile["speed"] + profile["setup"])

        # Suitability label is intentionally separate from the numeric score.
        suitability = (
            "Excellent" if score >= 85 else
            "Good" if score >= 70 else
            "Moderate" if score >= 50 else
            "Poor"
        )
        if not reasons:
            reasons.append("No major positive compatibility rule was triggered")
        if not risks:
            risks.append("No major process-specific risk was triggered by the prototype rules")

        rows.append({
            "process": process,
            "score": score,
            "suitability": suitability,
            "unit_low": estimated_low,
            "unit_high": estimated_high,
            "minutes": estimated_time,
            "reasons": reasons,
            "risks": risks,
        })

    rows.sort(key=lambda r: (r["score"], -r["unit_low"], -r["minutes"]), reverse=True)
    return rows


def complex_feature_count(d):
    count = 0
    if float(d.get("pocket_depth", 0)) > 0:
        count += 1
    if float(d.get("radius", 0)) > 0:
        count += 1
    if float(d.get("hole_dia", 0)) > 0:
        count += 1
    return count


def project_what_if(d, new_radius):
    copy = dict(d)
    copy["radius"] = float(new_radius)
    return analyze_design(copy)["score"]



def _optimization_candidate(d, parameter, current, proposed, reason, benefit):
    candidate = dict(d)
    candidate[parameter] = proposed
    result = analyze_design(candidate)
    return {
        "parameter": parameter,
        "current": current,
        "proposed": proposed,
        "reason": reason,
        "benefit": benefit,
        "analysis": result,
    }


def optimize_design(d):
    """Generate deterministic, reviewable design-improvement candidates.

    This does not modify CAD geometry. It evaluates parameter alternatives using
    the same DFM rules engine and returns the best non-destructive proposal.
    All recommendations are conditional on functional requirements being met.
    """
    original = analyze_design(dict(d))
    candidates = []

    radius = float(d["radius"])
    wall = float(d["wall"])
    pocket_depth = float(d["pocket_depth"])
    pocket_width = max(float(d["pocket_width"]), 0.1)
    hole_dia = float(d["hole_dia"])
    hole_depth = float(d["hole_depth"])
    tolerance = float(d["tolerance"])
    surface_ra = float(d["surface_ra"])

    # Only suggest changes where the current value is actually problematic.
    if radius < 3.0:
        proposed = 3.0 if radius <= 2.0 else 4.0
        candidates.append(_optimization_candidate(
            d, "radius", radius, proposed,
            "Increase a small internal radius to reduce small-tool requirements.",
            "Better cutter accessibility and potentially shorter machining time."
        ))

    if wall < 3.0:
        proposed = 3.0
        candidates.append(_optimization_candidate(
            d, "wall", wall, proposed,
            "Increase a thin wall where structural requirements allow it.",
            "Improved rigidity, lower deflection and more stable machining."
        ))

    ratio = pocket_depth / pocket_width
    if ratio > 2.0:
        # Target a more comfortable depth/width ratio without making an
        # extreme geometric jump. If the pocket is already reasonably wide,
        # reduce depth only as a secondary alternative.
        target_width = max(pocket_width, pocket_depth / 2.0)
        target_width = min(target_width, pocket_width * 2.0)
        if target_width > pocket_width + 0.01:
            candidates.append(_optimization_candidate(
                d, "pocket_width", pocket_width, round(target_width, 2),
                "Widen a deep/narrow pocket if surrounding geometry permits.",
                "Improved tool rigidity and accessibility."
            ))
        if pocket_depth > 10:
            target_depth = max(10.0, pocket_width * 2.0)
            if target_depth < pocket_depth - 0.01:
                candidates.append(_optimization_candidate(
                    d, "pocket_depth", pocket_depth, round(target_depth, 2),
                    "Reduce pocket depth if the functional envelope allows it.",
                    "Lower long-reach tooling risk and cycle time."
                ))

    if tolerance < 0.05:
        candidates.append(_optimization_candidate(
            d, "tolerance", tolerance, 0.05,
            "Relax a tight general tolerance where function does not require precision.",
            "Lower inspection and process-control burden."
        ))

    if surface_ra < 1.6:
        candidates.append(_optimization_candidate(
            d, "surface_ra", surface_ra, 1.6,
            "Relax an unusually fine finish where surface function permits it.",
            "Can avoid additional finishing operations."
        ))

    if hole_dia > 0 and hole_depth / max(hole_dia, 0.1) > 5.0:
        # We do not automatically change hole geometry because this can be a
        # functional requirement. Instead, evaluate a shallower alternative and
        # explicitly label it as requiring functional verification.
        proposed_depth = max(hole_dia * 5.0, 1.0)
        if proposed_depth < hole_depth - 0.01:
            candidates.append(_optimization_candidate(
                d, "hole_depth", hole_depth, round(proposed_depth, 2),
                "Consider reducing deep-hole depth only if the required engagement is maintained.",
                "Reduced drilling difficulty and chip-evacuation risk."
            ))

    evaluated = sorted(
        candidates,
        key=lambda c: (
            c["analysis"]["score"] - original["score"],
            original["unit_low"] - c["analysis"]["unit_low"],
            original["minutes"] - c["analysis"]["minutes"],
        ),
        reverse=True,
    )

    # Build a cumulative proposal from the strongest candidates, re-evaluating
    # after every accepted change. This makes the final proposal internally
    # consistent rather than combining independent one-change simulations.
    optimized = dict(d)
    applied = []
    remaining = list(evaluated)

    while remaining:
        best_step = None
        best_result = None
        current_result = analyze_design(optimized)

        for candidate in remaining:
            trial = dict(optimized)
            trial[candidate["parameter"]] = candidate["proposed"]
            trial_result = analyze_design(trial)
            score_gain = trial_result["score"] - current_result["score"]
            cost_gain = current_result["unit_low"] - trial_result["unit_low"]
            time_gain = current_result["minutes"] - trial_result["minutes"]
            key = (score_gain, cost_gain, time_gain)
            if best_step is None or key > best_step[0]:
                best_step = (key, candidate)
                best_result = trial_result

        if best_step is None or best_step[0][0] <= 0:
            break

        candidate = best_step[1]
        old_value = optimized[candidate["parameter"]]
        optimized[candidate["parameter"]] = candidate["proposed"]
        applied.append({
            "parameter": candidate["parameter"],
            "current": old_value,
            "proposed": candidate["proposed"],
            "reason": candidate["reason"],
            "benefit": candidate["benefit"],
        })
        remaining = [
            c for c in remaining if c["parameter"] != candidate["parameter"]
        ]

    optimized_result = analyze_design(optimized)

    return {
        "original": original,
        "optimized": optimized_result,
        "changes": applied,
        "candidate_count": len(candidates),
        "improved": optimized_result["score"] > original["score"],
        "score_gain": optimized_result["score"] - original["score"],
        "cost_reduction_pct": round(
            max(0.0, (original["unit_low"] - optimized_result["unit_low"])
                 / max(original["unit_low"], 0.01) * 100.0), 1
        ),
        "time_reduction_pct": round(
            max(0.0, (original["minutes"] - optimized_result["minutes"])
                 / max(original["minutes"], 0.01) * 100.0), 1
        ),
    }
