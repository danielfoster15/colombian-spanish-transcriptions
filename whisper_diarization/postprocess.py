"""Highlight informal second-person-singular (voseo/tuteo) verb forms in HTML transcripts.

Reads every transcript in <dir>/original/ and writes a copy to <dir>/modified/
with matching tokens wrapped in <mark> tags.

Usage:
    wd-highlight --dir my_transcripts --spacy-model es_dep_news_trf
"""

import argparse
import os

from bs4 import BeautifulSoup

MARK_STYLE = """
    mark {
        background-color: yellow;
        color: black;
        font-weight: bold;
    }
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Highlight 2nd-person-singular verb forms in HTML transcripts."
    )
    parser.add_argument("--dir", required=True,
                        help="Directory containing an original/ subfolder of HTML transcripts.")
    parser.add_argument("--spacy-model", default="es_dep_news_trf",
                        help="spaCy model to use (default: es_dep_news_trf).")
    return parser.parse_args()


def process_transcript(path, nlp):
    with open(path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    h2_tag = soup.find("h2")
    title_tag = soup.find("title")
    if h2_tag and title_tag:
        title_tag.string = h2_tag.text

    divs = soup.find_all("div", class_="t") or soup.find_all("span", class_="t")
    for i, div in enumerate(divs, start=1):
        doc = nlp(div.text)
        parts = []
        for token in doc:
            # token.whitespace_ preserves the original spacing that followed the
            # token, so punctuation stays attached ("Parce, ya." not "Parce , ya .").
            if "Person=2" in token.morph and "Number=Sing" in token.morph:
                parts.append(f"<mark>{token.text}</mark>{token.whitespace_}")
            else:
                parts.append(token.text_with_ws)
        div.clear()
        div.append(BeautifulSoup("".join(parts), "html.parser"))
        print(f"processed line {i} of {len(divs)} in {path}")

    style_tag = soup.new_tag("style")
    style_tag.string = MARK_STYLE
    soup.head.insert(0, style_tag)
    return soup


def main():
    args = parse_args()
    original_dir = os.path.join(args.dir, "original")
    modified_dir = os.path.join(args.dir, "modified")
    if not os.path.isdir(original_dir):
        raise SystemExit(f"{original_dir} not found — put source HTML transcripts there.")
    os.makedirs(modified_dir, exist_ok=True)

    import spacy  # imported late: slow

    nlp = spacy.load(args.spacy_model)
    for name in sorted(os.listdir(original_dir)):
        if not name.endswith(".html"):
            continue
        print("processing file", name)
        soup = process_transcript(os.path.join(original_dir, name), nlp)
        with open(os.path.join(modified_dir, name), "w", encoding="utf-8") as f:
            f.write(str(soup))


if __name__ == "__main__":
    main()
