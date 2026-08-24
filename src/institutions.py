"""Heuristics for spotting Colombian institutions in free-text affiliation strings.

ADS affiliation strings are unstructured free text: sometimes the original
Spanish name, sometimes an ADS-normalized English translation (e.g.
"National University of Colombia" for Universidad Nacional, "Technical
University of Santander" for Universidad Industrial de Santander). We match
against a curated list of known name variants and fall back to a generic
bucket when the string clearly mentions Colombia but doesn't hit one of the
known names. Extend KNOWN_INSTITUTIONS as new variants show up in the data.
"""
from __future__ import annotations

import re

# (canonical short name, list of regex patterns to match, case-insensitive)
# Ordered so more specific patterns are listed before generic substrings that
# might otherwise collide with them.
KNOWN_INSTITUTIONS: list[tuple[str, list[str]]] = [
    ("Universidad de los Andes", [
        r"universidad de los andes", r"\buniandes\b", r"university of the andes",
    ]),
    ("Universidad Nacional de Colombia", [
        r"universidad nacional de colombia", r"\bunal\b",
        r"national university of colombia",
    ]),
    ("Universidad Industrial de Santander", [
        r"universidad industrial de santander", r"\buis\b",
        r"technical university of santander", r"industrial university of santander",
    ]),
    ("Universidad de Antioquia", [
        r"universidad de antioquia", r"\budea\b", r"university of antioquia",
    ]),
    ("Universidad del Valle", [
        r"universidad del valle", r"\bunivalle\b", r"university of the valley",
    ]),
    ("Universidad Pedagógica y Tecnológica de Colombia", [
        r"pedag[oó]gica y tecnol[oó]gica de colombia", r"\buptc\b",
    ]),
    ("Universidad Tecnológica de Pereira", [
        r"tecnol[oó]gica de pereira", r"technological university of pereira",
        r"technical university of pereira",
    ]),
    ("Universidad Tecnológica de Bolívar", [
        r"tecnol[oó]gica de bol[ií]var", r"\butb\b",
    ]),
    ("Universidad del Atlántico", [
        r"universidad del atl[aá]ntico", r"university of the atlantic",
    ]),
    ("Universidad de Nariño", [
        r"universidad de nari[ñn]o", r"university of narino", r"university of nari[ñn]o",
    ]),
    ("Universidad de Medellín", [
        r"universidad de medell[ií]n", r"university of medellin",
    ]),
    ("Universidad Distrital Francisco José de Caldas", [
        r"universidad distrital", r"university distrital",
    ]),
    ("Universidad EAFIT", [r"\beafit\b"]),
    ("Universidad Sergio Arboleda", [r"sergio arboleda"]),
    ("Universidad ICESI", [r"\bicesi\b"]),
    ("Pontificia Universidad Javeriana", [
        r"pontificia universidad javeriana", r"\bjaveriana\b",
    ]),
    ("Universidad del Norte", [r"universidad del norte"]),
    ("Universidad Antonio Nariño", [
        r"universidad antonio nari[ñn]o", r"\buan\b",
    ]),
    ("Universidad de Cartagena", [r"universidad de cartagena"]),
    ("Universidad del Magdalena", [r"universidad del magdalena"]),
    ("Universidad del Cauca", [r"universidad del cauca"]),
    ("Universidad de Córdoba", [r"universidad de c[oó]rdoba"]),
    ("Universidad del Quindío", [r"universidad del quind[ií]o"]),
    ("Universidad del Tolima", [r"universidad del tolima"]),
    ("Universidad Autónoma de Occidente", [r"aut[oó]noma de occidente"]),
    ("Universidad Autónoma del Caribe", [r"aut[oó]noma del caribe"]),
    ("Universidad Militar Nueva Granada", [r"militar nueva granada"]),
    ("Universidad de Ibagué", [r"universidad de ibagu[eé]"]),
    ("Universidad de los Llanos", [r"universidad de los llanos"]),
    ("Universidad El Bosque", [r"universidad el bosque", r"universidad del bosque"]),
    ("Universidad ECCI", [r"universidad ecci"]),
    ("Universidad Ean", [r"universidad ean"]),
    ("Fundación Universitaria Konrad Lorenz", [r"konrad lorenz"]),
    ("Fundación Universitaria Los Libertadores", [r"los libertadores"]),
    ("Universidad de Investigación y Desarrollo", [r"universidad de investigaci[oó]n y desarrollo", r"\budi\b"]),
    ("Universidad Colegio Mayor de Cundinamarca", [r"colegio mayor de cundinamarca"]),
    ("International Center for Relativistic Astrophysics Network (ICRANet-Colombia)", [
        r"icranet.*colombia", r"international center for relativistic astrophysics.*colombia",
    ]),
    ("Observatorio Astronómico Nacional", [r"observatorio astron[oó]mico nacional", r"\boan\b"]),
    ("Planetario de Bogotá", [r"planetario de bogot[aá]"]),
    ("Parque Explora", [r"parque explora"]),
    ("Instituto de Astrobiología de Colombia", [r"astrobiolog[ií]a de colombia"]),
    ("COLCIENCIAS / MinCiencias", [r"colciencias", r"minciencias"]),
    ("Colombian Air Force (FAC/EMAVI)", [r"colombian air force", r"\bemavi\b"]),
]


def match_institution(affiliation: str) -> tuple[str | None, bool]:
    """Return (canonical_institution_or_None, is_colombian)."""
    if not affiliation:
        return None, False
    text = affiliation.lower()
    is_colombian = "colombia" in text
    for canonical, patterns in KNOWN_INSTITUTIONS:
        for pat in patterns:
            if re.search(pat, text):
                return canonical, True
    if is_colombian:
        return "Other Colombian institution", True
    return None, False
