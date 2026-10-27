"""
build_meanings.py <addon_dir> <jitendex-yomitan.zip>  →  <addon_dir>/meanings.json

English meanings for the hover text, from Jitendex (jitendex.org, CC BY-SA
4.0; JMdict content). Only words on the bundled lists are included: the
JLPT lists (jlpt_n*.txt), the top-20,000 frequency list (freq_bccwj.txt)
and the compounds freq_data adds as tiles (freq_extra.txt "e" rows).

Matching: a list word (display, reading, alternate spellings) takes the
Jitendex entry whose term is the display (or else one of its alternate
spellings) AND whose reading is the list reading (katakana = hiragana).
Several JMdict entries for the same pair: the highest Yomitan score (common
words first). So 汚れ よごれ (dirt) and 汚れ けがれ (impurity) differ.

Output (compact JSON):
  "k": {"display\\treading": seq}          — list word → JMdict sequence
  "m": {seq: [total_senses, [[pos, gloss], …]]}
       first 7 senses only; pos is "" when it repeats the previous sense's
  "source": Jitendex index title (e.g. "Jitendex.org [2026-10-03]")

Run: python -I -X utf8 tools/build_meanings.py <addon_dir> <zip>
"""

import json
import os
import re
import sys
import zipfile

MAX_SENSES = 7


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def text_of(node) -> str:
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(text_of(n) for n in node)
    if isinstance(node, dict):
        if node.get("tag") == "rt":
            return ""
        return text_of(node.get("content", ""))
    return ""


def _dc(node) -> str:
    return (node.get("data") or {}).get("content", "") if isinstance(node, dict) else ""


def _children(node):
    c = node.get("content") if isinstance(node, dict) else node
    if c is None:
        return []
    return c if isinstance(c, list) else [c]


# JMdict's long part-of-speech names → short hover labels.
_POS_SHORT = [
    (r"^noun or participle which takes the aux\. verb suru$", "する verb"),
    (r"^suru verb.*", "する verb"),
    (r"^Godan verb.*", "Godan verb"),
    (r"^Ichidan verb.*", "Ichidan verb"),
    (r"^Kuru verb.*", "Kuru verb"),
    (r"^transitive verb$", "transitive"),
    (r"^intransitive verb$", "intransitive"),
    (r"^adjectival nouns or quasi-adjectives.*", "na-adjective"),
    (r"^nouns which may take the genitive case particle 'no'$", "no-adjective"),
    (r"^adjective$", "i-adjective"),
    (r"^adverb taking the 'to' particle$", "to-adverb"),
    (r"^pre-noun adjectival.*", "pre-noun adjective"),
    (r"^noun, used as a suffix$", "suffix noun"),
    (r"^noun, used as a prefix$", "prefix noun"),
    (r"^expressions.*", "expression"),
]


def _clean_pos(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)", "", title).strip()
    for pat, short in _POS_SHORT:
        if re.match(pat, t):
            return short
    return t


def parse_senses(glossary) -> list[tuple[str, str]]:
    """[(part of speech, "gloss; gloss")] in order, from Yomitan structured
    content. Example sentences, forms and attribution are skipped."""
    senses: list[tuple[str, str]] = []

    def find_glosses(node) -> list[str]:
        out = []
        if isinstance(node, dict):
            if _dc(node) == "glossary":
                for li in _children(node):
                    t = text_of(li).strip()
                    if t:
                        out.append(t)
                return out
            if _dc(node) in ("extra-info", "example-sentence", "attribution", "forms"):
                return out
        for ch in (_children(node) if isinstance(node, (dict, list)) else []):
            out += find_glosses(ch)
        return out

    def find_info_gloss(node) -> list[str]:
        """A sense with no glossary may carry an explanation instead."""
        if isinstance(node, dict) and _dc(node) == "info-gloss-content":
            t = text_of(node).strip()
            return [t] if t else []
        out = []
        for ch in (_children(node) if isinstance(node, (dict, list)) else []):
            out += find_info_gloss(ch)
        return out

    def walk(node, pos: str):
        if isinstance(node, list):
            for n in node:
                walk(n, pos)
            return
        if not isinstance(node, dict):
            return
        kind = _dc(node)
        if kind in ("forms", "attribution", "extra-info"):
            return
        if kind == "sense-group":
            titles = []
            for ch in _children(node):
                if isinstance(ch, dict) and _dc(ch) == "part-of-speech-info":
                    t = _clean_pos(ch.get("title") or text_of(ch))
                    if t and t not in titles:
                        titles.append(t)
            pos = ", ".join(titles)
            for ch in _children(node):
                walk(ch, pos)
            return
        if kind == "sense":
            g = find_glosses(node) or find_info_gloss(node)
            if g:
                senses.append((pos, "; ".join(g)))
            return
        for ch in _children(node):
            walk(ch, pos)

    for item in glossary:
        if isinstance(item, dict) and item.get("type") == "structured-content":
            walk(item.get("content"), "")
        elif isinstance(item, str):
            senses.append(("", item))
    return senses


def load_jitendex(path: str):
    z = zipfile.ZipFile(path)
    title = json.loads(z.read("index.json")).get("title", "Jitendex")
    index: dict[tuple[str, str], list[tuple[int, int]]] = {}   # (term, reading) → [(score, seq)]
    glossaries: dict[int, list] = {}
    for name in z.namelist():
        if not name.startswith("term_bank"):
            continue
        for term, reading, _tags, _rules, score, glossary, seq, _tt in json.loads(z.read(name)):
            reading = reading or term
            index.setdefault((term, kata_to_hira(reading)), []).append((score, seq))
            glossaries.setdefault(seq, glossary)
    return title, index, glossaries


def redirect_target(glossary):
    """(term, reading) a Jitendex redirect entry (negative sequence, e.g.
    ウエートレス ⟶ ウェイトレス) points to, or None."""
    from urllib.parse import parse_qs, urlparse
    def find_a(node):
        if isinstance(node, dict):
            if node.get("tag") == "a":
                return node
            node = node.get("content")
        if isinstance(node, list):
            for n in node:
                hit = find_a(n)
                if hit:
                    return hit
        return None
    for item in glossary:
        a = find_a(item.get("content") if isinstance(item, dict) else None)
        if a:
            term = text_of(a).strip()
            q = parse_qs(urlparse(a.get("href", "")).query)
            reading = (q.get("primary_reading") or [term])[0]
            return term, kata_to_hira(reading)
    return None


def pick(hits, index, glossaries):
    """Best real entry: the highest score among positive sequences; a
    redirect is followed to its target."""
    real = [h for h in hits if h[1] > 0]
    if real:
        return max(real, key=lambda h: h[0])[1]
    for _score, seq in sorted(hits, reverse=True):
        target = redirect_target(glossaries[seq])
        if target:
            real = [h for h in index.get(target, []) if h[1] > 0]
            if real:
                return max(real, key=lambda h: h[0])[1]
    return None


def list_words(addon_dir: str):
    """(display, reading, [alt spellings]) for every JLPT and frequency word."""
    words = []
    for lvl in ("n5", "n4", "n3", "n2", "n1"):
        with open(os.path.join(addon_dir, f"jlpt_{lvl}.txt"), encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                cols = line.rstrip("\n").split("\t")
                alts = [a for a in (cols[2].split("|") if len(cols) > 2 else []) if a]
                words.append((cols[0], cols[1] if len(cols) > 1 and cols[1] else cols[0], alts))
    with open(os.path.join(addon_dir, "freq_bccwj.txt"), encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            alts = [a for a in (cols[3].split("|") if len(cols) > 3 else []) if a]
            words.append((cols[0], cols[1] or cols[0], alts))
    # The compounds freq_data adds as tiles (可能性, 日本語, 考え方: freq_extra
    # "e" rows up to COMPOUND_RANK_LIMIT), under the display/reading the
    # tile gets. Their parts of speech also let the sentence parser read them.
    import importlib.util
    spec = importlib.util.spec_from_file_location("freq_splits", os.path.join(addon_dir, "freq_splits.py"))
    fs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fs)
    with open(os.path.join(addon_dir, "freq_extra.txt"), encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if line.startswith("#") or len(cols) < 4 or cols[3] != "e":
                continue
            try:
                if int(cols[2]) > fs.COMPOUND_RANK_LIMIT:
                    continue
            except ValueError:
                continue
            d, rd = cols[0], cols[1] or cols[0]
            alts = [d] + [a for a in (cols[4].split("|") if len(cols) > 4 else []) if a]
            words.append((fs.COMPOUND_DISPLAY.get(d, d), fs.COMPOUND_READING.get(d, rd), alts))
    return words


def main():
    addon_dir, zip_path = sys.argv[1], sys.argv[2]
    sys.stdout.reconfigure(encoding="utf-8")
    title, index, glossaries = load_jitendex(zip_path)

    keys: dict[str, int] = {}
    unmatched = []
    for display, reading, alts in list_words(addon_dir):
        key = f"{display}\t{reading}"
        if key in keys:
            continue
        r = kata_to_hira(reading)
        hits = []
        for form in [display] + alts:
            hits = index.get((form, r), [])
            if hits:
                break
        # する-verbs and と/に adverbs are listed whole (コピーする, ゆっくりと);
        # JMdict has the base word.
        for suffix in ("する", "と", "に"):
            if hits:
                break
            if display.endswith(suffix) and r.endswith(suffix) and len(display) > len(suffix):
                rb = r[: -len(suffix)]
                # Alternate spellings may already be the base (あいさつする: 挨拶).
                for form in [display] + alts:
                    base = form[: -len(suffix)] if form.endswith(suffix) else form
                    hits = index.get((base, rb), [])
                    if hits:
                        break
        if not hits:
            unmatched.append(key)
            continue
        seq = pick(hits, index, glossaries)
        if seq is None:
            unmatched.append(key)
            continue
        keys[key] = seq

    meanings: dict[str, list] = {}
    no_senses = 0
    for seq in set(keys.values()):
        senses = parse_senses(glossaries[seq])
        if not senses:
            no_senses += 1
            print("no senses:", seq, json.dumps(glossaries[seq], ensure_ascii=False)[:300])
            continue
        shown, prev = [], None
        for pos, gloss in senses[:MAX_SENSES]:
            shown.append(["" if pos == prev else pos, gloss])
            prev = pos
        meanings[str(seq)] = [len(senses), shown]
    keys = {k: s for k, s in keys.items() if str(s) in meanings}

    out = os.path.join(addon_dir, "meanings.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"source": title, "k": keys, "m": meanings}, f,
                  ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"{title}: {len(keys):,} words → {len(meanings):,} entries; "
          f"{len(unmatched):,} unmatched, {no_senses} without senses; "
          f"{os.path.getsize(out) / 1e6:.2f} MB")
    print("unmatched sample:", unmatched[:40])


if __name__ == "__main__":
    main()
