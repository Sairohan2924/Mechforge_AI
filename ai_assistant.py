from __future__ import annotations

import os
import re
from typing import Any

SYSTEM = '''You are MechForge AI, a universal engineering and general-purpose assistant built into MechForge AI.

You can answer a broad range of questions: mechanical engineering, manufacturing, DFM/DFA, CAD, GD&T, materials, machining, metrology, design calculations, engineering interview questions, Python/programming, software, mathematics, science, career/learning questions, writing/rewriting, general knowledge, and normal conversational questions.

IMPORTANT BEHAVIOUR:
1. Answer the user's actual question directly. Do NOT require a DFM analysis for a general question.
2. Use the attached MechForge DFM/CAD context when it is relevant to the question, but do not force unrelated project data into the answer.
3. For questions about the current design, treat deterministic DFM results and parsed CAD geometry as the source of truth. Explain the engineering reasoning instead of merely repeating a score.
4. Never invent dimensions, tolerances, GD&T, material properties, certifications, supplier commitments, measurements, or project facts. If a project value is unavailable, say so.
5. Clearly distinguish extracted/measured values, deterministic rule results, engineering inference, and general knowledge.
6. For calculations, show the formula and assumptions when useful, and check units.
7. For safety-critical, production, legal, medical, financial, or certification-sensitive questions, provide useful information but state relevant limitations and recommend qualified verification where appropriate.
8. If the question is ambiguous, make the most reasonable interpretation and answer it, then briefly state what assumption you made. Ask a clarifying question only when it is genuinely necessary.
9. Do not repeatedly tell the user to ask a narrower question. You are expected to handle follow-up questions and topic changes naturally.
10. Be practical, clear, and technically accurate. Use headings, bullets, tables, equations, or examples when they improve the answer.'''


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _fmt_mm(value, decimals=2):
    v = _num(value)
    return f"{v:.{decimals}f} mm"


def _context_summary(a: dict[str, Any], cad: dict[str, Any]) -> str:
    if not a and not cad:
        return "No DFM analysis or CAD context is attached yet."

    lines = []
    if a:
        lines.append(f"DFM: {a.get('score', '—')}/100 ({a.get('classification', '—')}).")
        lines.append(f"Recommended process: {a.get('recommended_process', '—')} (confidence {a.get('confidence', '—')}%).")
        lines.append(
            "Design inputs: "
            f"wall {_fmt_mm(a.get('wall'))}, radius {_fmt_mm(a.get('radius'))}, "
            f"pocket {_fmt_mm(a.get('pocket_depth'))} deep × {_fmt_mm(a.get('pocket_width'))} wide, "
            f"hole Ø{_num(a.get('hole_dia')):g} mm × {_fmt_mm(a.get('hole_depth'))}, "
            f"tolerance ±{_num(a.get('tolerance')):.3f} mm, Ra {_num(a.get('surface_ra')):g} µm."
        )
        lines.append(f"Material: {a.get('material', '—')}. Quantity: {a.get('quantity', '—')}.")
        lines.append(f"Estimated unit cost: ₹{_num(a.get('unit_low')):,.0f}–₹{_num(a.get('unit_high')):,.0f}. Estimated machining time: {_num(a.get('minutes')):.1f} min.")
        reasons = a.get('reasons') or []
        if reasons:
            lines.append("Process reasons: " + " | ".join(str(x) for x in reasons))
        issues = a.get('issues') or []
        if issues:
            lines.append("DFM findings: " + " | ".join(
                f"{i.get('priority','')}: {i.get('title','')}; recommendation: {i.get('recommendation','')}"
                for i in issues
            ))
    if cad:
        b = cad.get('bbox') or {}
        lines.append(
            f"CAD: {cad.get('format','—')}, {cad.get('solids',0)} solids, {cad.get('faces',0)} faces, "
            f"{cad.get('edges',0)} edges, bounding box {_num(b.get('x')):.2f} × {_num(b.get('y')):.2f} × {_num(b.get('z')):.2f} mm, "
            f"volume {_num(cad.get('volume_mm3')):,.0f} mm³."
        )
    return "\n".join(lines)


def _fallback(question: str, analysis=None, cad=None, history=None):
    a = analysis or {}
    c = cad or {}
    q = (question or '').strip().lower()
    issues = a.get('issues') or []
    high = [i for i in issues if str(i.get('priority', '')).upper() == 'HIGH']
    medium = [i for i in issues if str(i.get('priority', '')).upper() == 'MEDIUM']
    process = a.get('recommended_process') or '—'
    reasons = a.get('reasons') or []
    score = a.get('score')

    if not a and c:
        b = c.get('bbox') or {}
        return (
            f"The attached CAD model is {c.get('format','—')} with {c.get('solids',0)} solid body/bodies, "
            f"{c.get('faces',0)} faces and {c.get('edges',0)} edges. Its bounding box is "
            f"{_num(b.get('x')):.2f} × {_num(b.get('y')):.2f} × {_num(b.get('z')):.2f} mm. "
            "The CAD parser provides geometry-level evidence; functional intent, GD&T and manufacturing notes "
            "still need drawing/user inputs."
        )

    # Process-selection questions: use the actual deterministic reasons.
    if any(k in q for k in ('why', 'reason', 'recommended', 'recommend', 'process')) and any(k in q for k in ('cnc', 'milling', 'turning', 'manufactur')):
        reason_text = "; ".join(str(x) for x in reasons) if reasons else "the deterministic process-selection rules selected it"
        if process == 'CNC Milling':
            feature_reason = (
                f"The supplied design contains a {_num(a.get('pocket_depth')):g} mm-deep × {_num(a.get('pocket_width')):g} mm-wide pocket, "
                f"a {_num(a.get('radius')):g} mm internal radius and a Ø{_num(a.get('hole_dia')):g} mm hole, "
                "which are all compatible with conventional CNC milling/drilling operations. "
                f"{a.get('material','The selected material')} is also considered in the process assessment."
            )
        else:
            feature_reason = "The supplied geometry, material, quantity and DFM requirements are used by the process assessment."
        return (
            f"**{process} was recommended because:** {reason_text}.\n\n"
            f"{feature_reason}\n\n"
            f"The current DFM result is **{score}/100 ({a.get('classification','—')})**. "
            "The recommendation is based on the supplied geometry, material, quantity and DFM requirements; "
            "it is not a certification or a live supplier decision."
        )

    # Risk / improvement questions: report actual findings first, then actionable improvements.
    if any(k in q for k in ('risk', 'risks', 'improve', 'improvement', 'problem', 'issue', 'top 3')):
        if high or medium:
            ranked = high + medium
            bullets = []
            for i in ranked[:3]:
                bullets.append(
                    f"**{i.get('priority','')} — {i.get('title','')}**: observed {i.get('observed','—')}. "
                    f"{i.get('recommendation','Review the feature.') }"
                )
            return (
                f"The design scores **{score}/100 ({a.get('classification','—')})**. "
                f"I found {len(high)} HIGH and {len(medium)} MEDIUM finding(s).\n\n" +
                "### Top DFM actions\n" + "\n".join(f"{n}. {b}" for n, b in enumerate(bullets, 1)) +
                "\n\nThese are rule-based recommendations; verify functional requirements before changing geometry."
            )
        return (
            f"There are currently **no HIGH or MEDIUM DFM findings**. The design scores **{score}/100 ({a.get('classification','—')})**.\n\n"
            "Top improvement actions are therefore preventive rather than corrective:\n"
            "1. Retain the current geometry unless function requires a change.\n"
            "2. Avoid adding tighter tolerances or finer surface finishes without a functional need.\n"
            "3. Re-check process economics if production quantity changes.\n\n"
            "The current deterministic rules do not identify a major DFM risk."
        )

    # Score / summary questions.
    if any(k in q for k in ('score', 'dfm', 'manufacturability', 'summary', 'overall')):
        breakdown = a.get('breakdown') or {}
        bd = ", ".join(f"{k} {v}/100" for k, v in breakdown.items())
        return (
            f"**DFM score: {score}/100 — {a.get('classification','—')}**.\n\n"
            f"Recommended process: **{process}**. Material: **{a.get('material','—')}**. Quantity: **{a.get('quantity','—')}**.\n"
            f"Key inputs: wall {_fmt_mm(a.get('wall'))}, radius {_fmt_mm(a.get('radius'))}, "
            f"pocket {_fmt_mm(a.get('pocket_depth'))} deep / {_fmt_mm(a.get('pocket_width'))} wide, "
            f"hole Ø{_num(a.get('hole_dia')):g} × {_fmt_mm(a.get('hole_depth'))}, "
            f"±{_num(a.get('tolerance')):.3f} mm, Ra {_num(a.get('surface_ra')):g} µm.\n"
            f"Breakdown: {bd or 'not available'}."
        )

    # Cost / time questions.
    if any(k in q for k in ('cost', 'price', 'expensive', 'time', 'minutes', 'machining')):
        return (
            f"The current prototype estimate is **₹{_num(a.get('unit_low')):,.0f}–₹{_num(a.get('unit_high')):,.0f} per unit** "
            f"with an estimated machining time of **{_num(a.get('minutes')):.1f} min/unit**. "
            f"Quantity is {a.get('quantity','—')}. These are transparent model estimates, not supplier quotations."
        )

    # CAD questions while a DFM analysis is also attached.
    if any(k in q for k in ('cad', 'geometry', 'model', 'solid', 'face', 'edge', 'bounding')) and c:
        b = c.get('bbox') or {}
        return (
            f"The CAD model is **{c.get('format','—')}** with **{c.get('solids',0)} solid(s)**, "
            f"{c.get('faces',0)} faces and {c.get('edges',0)} edges. Bounding box: "
            f"**{_num(b.get('x')):.2f} × {_num(b.get('y')):.2f} × {_num(b.get('z')):.2f} mm**. "
            f"Volume: **{_num(c.get('volume_mm3')):,.0f} mm³**."
        )

    # Common general-purpose questions can still receive a useful local answer
    # when no OpenAI key is configured. The cloud mode remains the full universal
    # assistant for arbitrary questions and topic changes.
    if not a and not c:
        if any(k in q for k in ('hello', 'hi ', 'hey', 'good morning', 'good evening')):
            return "Hey! 👋 I’m MechForge AI. You can ask me about engineering, CAD, manufacturing, DFM, Python, calculations, learning, or general questions."
        return (
            "I can handle general questions, but the local offline mode has limited reasoning compared with the cloud AI. "
            "Configure OPENAI_API_KEY in Settings for the full universal assistant, which can answer arbitrary topics and follow-up questions."
        )

    # General conversational questions while project context exists.
    if q in {'hi', 'hello', 'hey', 'hi there', 'hello there'}:
        return "Hey! 👋 I’m ready. Ask me anything, or ask about this MechForge design, CAD model, DFM, cost, manufacturing or optimization."

    if any(k in q for k in ('what is python', 'what is cad', 'what is dfm', 'what is cnc', 'what is gd&t', 'what is gdt')):
        if 'python' in q:
            return "Python is a general-purpose programming language widely used for automation, data analysis, engineering scripts, AI and application development."
        if 'dfm' in q:
            return "DFM (Design for Manufacturing) is the practice of designing a component so it can be manufactured reliably, economically and repeatably while meeting its functional requirements."
        if 'cnc' in q:
            return "CNC machining uses computer-controlled machine tools to remove material or perform operations such as milling, turning and drilling according to programmed toolpaths."
        if 'gd&t' in q or 'gdt' in q:
            return "GD&T (Geometric Dimensioning and Tolerancing) is a standardized method for specifying allowable variation in geometry, orientation, location and form relative to defined datums."
        return "CAD (Computer-Aided Design) is software-based creation and modification of engineering geometry, drawings and product models."

    return (
        f"Current MechForge context: DFM {score}/100 ({a.get('classification','—')}), recommended process {process}. "
        f"There are {len(high)} HIGH and {len(medium)} MEDIUM findings. "
        "The local offline assistant can answer the supported engineering questions from this context; configure OPENAI_API_KEY for unrestricted general-purpose Q&A."
    )


def _load_api_key():
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if key:
        return key
    try:
        import streamlit as st
        return str(st.secrets['OPENAI_API_KEY']).strip()
    except Exception:
        return ''


def answer(question, analysis=None, cad=None, history=None):
    key = _load_api_key()
    if not key:
        return _fallback(question, analysis, cad, history), 'Local engineering assistant'

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        context = _context_summary(analysis or {}, cad or {})
        prior = ''
        if history:
            prior = '\nRecent conversation:\n' + '\n'.join(
                f"{m.get('role','')}: {m.get('content','')}" for m in history[-6:]
            )
        prompt = f"MechForge engineering context:\n{context}{prior}\n\nUser question: {question}"
        response = client.responses.create(
            model=os.getenv('MECHFORGE_AI_MODEL', 'gpt-5.6-luna'),
            instructions=SYSTEM,
            input=[{'role': 'user', 'content': prompt}],
        )
        return response.output_text, 'OpenAI Responses API'
    except Exception as exc:
        return (
            _fallback(question, analysis, cad, history) +
            f"\n\nCloud AI unavailable; using local engineering fallback ({type(exc).__name__})."
        ), 'Local fallback'
