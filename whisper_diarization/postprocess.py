"""Highlight informal second-person-singular (voseo/tuteo) forms in HTML transcripts.

Reads every transcript in <dir>/original/ and writes a copy to <dir>/modified/
with each 2nd-person-singular token wrapped in a colored <mark>:

- voseo   (green)  : vos, and voseo-exclusive verb forms (tenés, sabés, vení, sos)
- tuteo   (orange) : tú, and tú-exclusive verb forms (tienes, mira)
- neutral (grey)   : usted, te/ti/tu clitics, and forms shared by both
                     paradigms (preterite/imperfect/future/subjunctive)

spaCy's tagger sometimes analyses paisa vocatives and proper names as 2nd-person
imperatives of invented verbs (parce -> "parzar", cande -> "candar"). Those
surface forms are listed in DEFAULT_EXCLUDE and can be extended with --exclude.

Usage:
    wd-highlight --dir my_transcripts --spacy-model es_dep_news_trf
    wd-highlight --dir my_transcripts --exclude parce,cande,mija
"""

import argparse
import os
import re

from bs4 import BeautifulSoup

# Surface forms spaCy mis-tags as 2nd-person verbs (paisa vocatives, names).
DEFAULT_EXCLUDE = {"parce", "parcero", "parceros", "cande", "anguesa", "tomitas"}

VOSEO_PRONOUNS = {"vos"}
NEUTRAL_PRONOUNS = {"usted", "te", "ti", "tu", "tuya", "tuyo", "tuyas", "tuyos",
                    "os", "vosotros", "ustedes"}
# Present-indicative forms identical in the tú and vos paradigms.
AMBIGUOUS_PRESENT = {"estás", "das", "vas"}

MARK_STYLE = """
    mark { background: none; }
    mark.voseo   { background-color: #b5e8c9; color: #000; font-weight: bold; }
    mark.tuteo   { background-color: #ffe0a3; color: #000; font-weight: bold; }
    mark.neutral { background-color: #e2e2e2; color: #000; }
"""

LEGEND = (
    '<p style="font-family:sans-serif;font-size:14px">'
    '<mark class="voseo">voseo</mark> '
    '<mark class="tuteo">tuteo</mark> '
    '<mark class="neutral">usted / shared 2nd-person</mark></p>'
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Highlight 2nd-person-singular (voseo/tuteo) forms in HTML transcripts."
    )
    parser.add_argument("--dir", required=True,
                        help="Directory containing an original/ subfolder of HTML transcripts.")
    parser.add_argument("--spacy-model", default="es_dep_news_trf",
                        help="spaCy model to use (default: es_dep_news_trf).")
    parser.add_argument("--exclude", default="",
                        help="Extra comma-separated surface forms to never highlight "
                             "(added to the built-in vocative/name stoplist).")
    return parser.parse_args()


def classify_2p(token):
    """Return 'voseo', 'tuteo', 'neutral', or None (not a 2nd-person-singular form)."""
    if "Person=2" not in token.morph or "Number=Sing" not in token.morph:
        return None
    w = token.text.lower()
    if w in VOSEO_PRONOUNS:
        return "voseo"
    if w == "tú":
        return "tuteo"
    if w in NEUTRAL_PRONOUNS:
        return "neutral"
    if token.pos_ in ("VERB", "AUX"):
        mood = token.morph.get("Mood")
        tense = token.morph.get("Tense")
        if w == "sos":                      # irregular voseo of 'ser'
            return "voseo"
        if w in AMBIGUOUS_PRESENT:
            return "neutral"
        # Oxytone endings are the voseo diagnostic — an accented final vowel
        # (imperative vení, mirá, tené) or -ás/-és/-ís present (tenés, sabés).
        # spaCy often mislabels the mood of voseo imperatives, so key on the form.
        if re.search(r"[áéí]$", w):
            return "voseo"                  # imperative vení, mirá, tené
        if "Ind" in mood and "Fut" not in tense and re.search(r"[áéí]s$", w):
            return "voseo"                  # present indicative tenés, sabés (not subj. estés / future vivirás)
        if "Imp" in mood:                   # remaining imperatives are tú
            return "tuteo"
        if "Pres" in tense and "Ind" in mood:
            return "tuteo"                  # tienes, sabes, dices
        return "neutral"                    # preterite/imperfect/future/subjunctive: shared
    return "neutral"


def process_transcript(path, nlp, exclude):
    with open(path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    h2_tag = soup.find("h2")
    title_tag = soup.find("title")
    if h2_tag and title_tag:
        title_tag.string = h2_tag.text

    divs = soup.find_all("div", class_="t") or soup.find_all("span", class_="t")
    for i, div in enumerate(divs, start=1):
        parts = []
        for token in nlp(div.text):
            category = classify_2p(token)
            # token.whitespace_ preserves original spacing so punctuation stays
            # attached ("Parce, ya." not "Parce , ya .").
            if category and token.text.lower() not in exclude:
                parts.append(f'<mark class="{category}">{token.text}</mark>{token.whitespace_}')
            else:
                parts.append(token.text_with_ws)
        div.clear()
        div.append(BeautifulSoup("".join(parts), "html.parser"))
        print(f"processed line {i} of {len(divs)} in {path}")

    style_tag = soup.new_tag("style")
    style_tag.string = MARK_STYLE
    soup.head.insert(0, style_tag)
    if h2_tag:
        h2_tag.insert_after(BeautifulSoup(LEGEND, "html.parser"))
    return soup


def main():
    args = parse_args()
    original_dir = os.path.join(args.dir, "original")
    modified_dir = os.path.join(args.dir, "modified")
    if not os.path.isdir(original_dir):
        raise SystemExit(f"{original_dir} not found — put source HTML transcripts there.")
    os.makedirs(modified_dir, exist_ok=True)

    exclude = set(DEFAULT_EXCLUDE)
    exclude.update(w.strip().lower() for w in args.exclude.split(",") if w.strip())

    import spacy  # imported late: slow

    nlp = spacy.load(args.spacy_model)
    for name in sorted(os.listdir(original_dir)):
        if not name.endswith(".html"):
            continue
        print("processing file", name)
        soup = process_transcript(os.path.join(original_dir, name), nlp, exclude)
        with open(os.path.join(modified_dir, name), "w", encoding="utf-8") as f:
            f.write(str(soup))


if __name__ == "__main__":
    main()
