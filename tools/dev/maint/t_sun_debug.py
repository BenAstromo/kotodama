"""Bug: with the DEBUG 'Count all notes' switch on, a 20,000-note test deck
made _check_amaterasu_crossing write amaterasu_reached (permanent; part of the
Sun Diamond loyalty tier, mirrored into the collection and the Nakama card)."""
import stubenv as E
pd = E.load("progress_dialog")
E.CFG.update(debug_rank_count_all=True, rank_last_real_count=3000)
E.CFG.pop("amaterasu_reached", None)
fake = type("F", (), {})()
fake._rank_real_total = 20000          # what count_deck_notes returns with the debug switch on
fake._deck_name = "D"
pd.OverviewTab._check_amaterasu_crossing(fake, True, is_debug=False)
E.check("debug count does not set amaterasu_reached", not E.CFG.get("amaterasu_reached"))
E.CFG.update(debug_rank_count_all=False, rank_last_real_count=19999)
pd.OverviewTab._check_amaterasu_crossing(fake, True, is_debug=False)
E.check("a real 20,000 still sets amaterasu_reached", bool(E.CFG.get("amaterasu_reached")))
E.finish()
