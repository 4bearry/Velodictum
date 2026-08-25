"""
Velodictum - Personal Style & Tone Profiles
Allows customized tone adaptation (Formal Sie, Informal Du, Concise, Academic, Custom Instructions).
"""
from typing import Dict

TONE_PROFILES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "Standard (Auto)",
        "tag": "AUTO",
        "description": "Behält den natürlichen Tonfall der gesprochenen Eingabe bei.",
        "prompt_instruction": "",
    },
    "formal_sie": {
        "name": "Formell (Sie-Form)",
        "tag": "BUSINESS",
        "description": "Höflicher geschäftlicher Ton mit durchgehender 'Sie'-Anrede.",
        "prompt_instruction": "STIL-VORGABE: Formuliere im professionellen, höflichen Geschäftsdeutsch mit 'Sie'-Anrede (z.B. 'Könnten Sie bitte...').",
    },
    "informal_du": {
        "name": "Locker (Du-Form)",
        "tag": "CASUAL",
        "description": "Kollegialer, direkter Ton mit 'Du'-Anrede für Chat und Team.",
        "prompt_instruction": "STIL-VORGABE: Formuliere im freundlichen, kollegialen Ton mit 'Du'-Anrede.",
    },
    "concise": {
        "name": "Prägnant & Direkt",
        "tag": "BRIEF",
        "description": "Maximale Kürze ohne Füllfloskeln, ideal für schnelle Notizen und Action Items.",
        "prompt_instruction": "STIL-VORGABE: Fasse dich extrem kurz, präzise und schnörkellos. Entferne alle unnötigen Höflichkeitsfloskeln.",
    },
    "academic": {
        "name": "Akademisch & Gehoben",
        "tag": "EXPERT",
        "description": "Präziser Wortschatz, strukturierte Syntax und fundierter Ausdruck.",
        "prompt_instruction": "STIL-VORGABE: Verwende einen gehobenen, präzisen und wohlformulierten Wortschatz.",
    },
    "latex": {
        "name": "LaTeX & Mathe",
        "tag": "EXPERIMENTELL",
        "description": "Wandelt mathematische Diktate direkt in LaTeX-Formeln ($...$, \\[...\\]) und Syntax um.",
        "prompt_instruction": (
            "STIL-VORGABE (LATEX & MATHEMATISCHER FORMELSATZ - EXPERIMENTELL):\n"
            "1. MATHEMATISCHE FORMELN & NOTATION:\n"
            "   - Wandle alle mathematischen Variablen, Terme, Indizes, Integrale, Summen, Brüche, Grenzwerte und Gleichungen in syntaktisch korrektes LaTeX um.\n"
            "   - Setze Inline-Mathematik immer in $...$ (z.B. '$x_i$', '$\\alpha > 0$', '$f \\colon X \\to Y$', '$\\frac{a}{b}$', '$\\sum_{i=1}^n x_i$').\n"
            "   - Setze abgesetzte Formeln und Gleichungen in \\[ ... \\] oder \\begin{equation} ... \\end{equation}.\n"
            "2. STRUKTUR & BEFEHLE:\n"
            "   - 'Überschrift 1 / 2 / 3' -> \\section{...} / \\subsection{...} / \\subsubsection{...}\n"
            "   - 'Fett' -> \\textbf{...}, 'Kursiv' -> \\textit{...}\n"
            "   - 'Aufzählung / Stichpunkte' -> \\begin{itemize} \\item ... \\end{itemize}\n"
            "   - 'Nummerierte Liste' -> \\begin{enumerate} \\item ... \\end{enumerate}\n"
            "3. SONDERZEICHEN ESCAPEN:\n"
            "   - Escape im normalen Fließtext typische LaTeX-Sonderzeichen wie '\\%', '\\&', '\\_', '\\#'.\n"
            "4. SNIPPET-AUSGABE:\n"
            "   - Gib keinen \\documentclass-Header oder \\begin{document} aus, sondern nur das formatierte Snippet für die aktuelle Cursor-Position."
        ),
    },
}


def get_tone_instruction(tone_key: str, custom_instructions: str = "") -> str:
    """Combines tone profile instruction with any user-defined custom prompt instructions."""
    parts = []
    if tone_key in TONE_PROFILES and TONE_PROFILES[tone_key]["prompt_instruction"]:
        parts.append(TONE_PROFILES[tone_key]["prompt_instruction"])
    if custom_instructions and custom_instructions.strip():
        parts.append(f"ZUSÄTZLICHE NUTZER-ANWEISUNG: {custom_instructions.strip()}")
    return "\n".join(parts)
