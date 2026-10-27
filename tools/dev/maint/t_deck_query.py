"""Deck names with Anki search specials (_ * \ ") must be escaped in the
deck: search (Anki manual: _ and * are wildcards, \" ends the quote)."""
import stubenv as E
cs = E.load("card_state")
q = cs.deck_search('Core_2k')
E.check("underscore escaped", q == '"deck:Core\_2k" -is:new')
q = cs.deck_search('My "best" deck*', ignore_suspended=True, seen_only=False)
E.check("quote and star escaped", q == '"deck:My \\"best\\" deck\*" -is:suspended')
q = cs.deck_search('a' + chr(92) + 'b')
E.check("backslash escaped", q == '"deck:a' + chr(92) * 2 + 'b" -is:new')
q = cs.deck_search('Japanese::ベンの辞書')
E.check("plain subdeck name unchanged", q == '"deck:Japanese::ベンの辞書" -is:new')
kv = E.load("kanji_view")
src = open(kv.__file__, encoding="utf-8").read()
E.check("kanji_view builds deck queries through card_state", "deck_query(" in src and '"deck:{deck}"' not in src)
E.finish()
