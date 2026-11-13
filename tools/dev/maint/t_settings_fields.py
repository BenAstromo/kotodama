"""Settings field drop-downs (guide item 1): an existing config comes back
from get_config() with exactly the same mapping dicts (the history signature
hashes them), the drop-downs list the note type's fields, and OK refuses a
field name the note type doesn't have (offering the right case)."""
import stubenv as E
import mkcol

nts = {"Kaishi 1.5k": ["Word", "WordReading", "Sentence"],
       "Lapis": ["Expression", "ExpressionReading", "Sentence", "SentenceFurigana"],
       "Kanji": ["kanji", "Meaning"]}
E.mw.col = mkcol.Col(nts, ["Japanese", "Kanji deck"], [])
cd = E.load("config_dialog")

MAPS = [{"note_type": "Kaishi 1.5k", "field": "Word", "reading_field": "WordReading"},
        {"note_type": "Lapis", "field": "Expression", "reading_field": "ExpressionReading",
         "sentence_field": "Sentence"},
        {"note_type": "", "field": "", "reading_field": "", "sentence_field": "Sentence"}]
KSRC = {"mode": "fields", "deck": "Kanji deck", "mappings": [{"note_type": "Kanji", "field": "kanji"}]}
GSRC = {"mode": "sentence", "deck": "Japanese", "mappings": []}
cfg = {"deck_name": "Japanese", "field_mappings": [dict(m) for m in MAPS],
       "kanji_source": dict(KSRC), "grammar_source": dict(GSRC)}

dlg = cd.ConfigDialog(None, dict(cfg))
out = dlg.get_config()
E.check("field_mappings come back unchanged", out["field_mappings"] == MAPS)
E.check("kanji mappings come back unchanged", out["kanji_source"]["mappings"] == KSRC["mappings"])

row = dlg._rows[1]
items = [row.field_edit.itemText(i) for i in range(row.field_edit.count())]
E.check("a row lists its note type's fields (empty first)",
        items == ["", "Expression", "ExpressionReading", "Sentence", "SentenceFurigana"])
row.note_combo.setCurrentText("Kaishi 1.5k")
items = [row.field_edit.itemText(i) for i in range(row.field_edit.count())]
E.check("changing the note type refills the list and keeps the typed text",
        "Word" in items and "Expression" not in items and row.field_edit.currentText() == "Expression")
row.note_combo.setCurrentText("Lapis")
allrow = dlg._rows[2]
items = [allrow.field_edit.itemText(i) for i in range(allrow.field_edit.count())]
E.check("(all note types) lists every field once, sorted",
        items[0] == "" and items.count("Sentence") == 1 and "kanji" in items and "Word" in items)

# OK with all names right: accepted
dlg.accept()
E.check("OK with good names closes", dlg.result() == 1)

# a wrong case: OK asks, "yes" fixes it
dlg2 = cd.ConfigDialog(None, dict(cfg, field_mappings=[dict(MAPS[1], field="expression")]))
asked = []
import aqt.utils as U
U.askUser = lambda msg, **k: (asked.append(msg), True)[1]
dlg2.accept()
E.check("a wrong case is offered the right spelling", asked and "case-sensitive" in asked[0] and "Expression" in asked[0])
E.check("…and fixed after yes", dlg2.get_config()["field_mappings"][0]["field"] == "Expression" and dlg2.result() == 1)

# a name no note type has: warning, the dialog stays open
E.LOG["warnings"].clear()
dlg3 = cd.ConfigDialog(None, dict(cfg, field_mappings=[dict(MAPS[0], reading_field="Furigana")]))
dlg3.accept()
E.check("an unknown field is refused with a warning naming it",
        any("Furigana" in str(w) and "Vocab row 1" in str(w) for w in E.LOG["warnings"]) and dlg3.result() == 0)

# a kanji row's bad field is only checked when that source is used
dlg4 = cd.ConfigDialog(None, dict(cfg, kanji_source=dict(KSRC, mode="vocab", mappings=[{"note_type": "Kanji", "field": "Nope"}])))
dlg4.accept()
E.check("unused kanji rows aren't checked", dlg4.result() == 1)
E.finish()
