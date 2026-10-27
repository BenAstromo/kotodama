exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
from jlpt_progress import card_state
rows = freq_data.load()
loan0 = [i for i, r in enumerate(rows) if freq_data.is_english_loanword(r[0], r[1])]
entries = [(i + 1, r[0], r[1], None) for i, r in enumerate(rows)]
res = {"frequency": {"found_ranks": set(loan0) | {5}, "entries": entries}}   # + one non-loan word marked by hand
parts = card_state.found_parts(res)
print("hand:", parts["hand"], "| loans marked:", len(parts["loans"]), "| first ranks:", parts["loans"][:5])
fails = []
for cards, want in ((3160, 3411 + 1), (17464, 20000 + 1), (0, 1 + card_state.loans_counted(0, parts["loans"]))):
    got = card_state.rank_split(cards, parts)[0]
    print(f"cards {cards:,} → rank {got:,} (loans {card_state.loans_counted(cards, parts['loans']):,})", "ok" if got == want else f"FAIL want {want}")
    if got != want: fails.append(cards)
for total in (3412, 9000, 20001, 50):
    c, l = card_state.cards_for_rank(total, parts)
    back = card_state.rank_split(c, parts)[0]
    print(f"rank {total:,} → {c:,} cards + {l:,} loans + {parts['hand']} hand → back {back:,}", "ok" if back == total else "FAIL")
    if back != total: fails.append(total)
print("old stored int →", card_state._norm_found(2541))
print("FAILS:", fails or "none")
# ratio line: like with like (2026-10-21) — owner-like numbers, all loanwords marked
rank = card_state.rank_split(3160, parts)[0]
pending = card_state.loans_not_yet_counted(rank, parts)
common = 2631 + 2536                                   # common words known: cards + every marked loanword
adj = common - pending
print(f"rank {rank:,}; common known {common:,}; not yet counted {pending:,} → common for the ratio {adj:,} → {min(100, round(adj / rank * 100))}%, {max(0, rank - adj):,} outside")
print("at 17,464 cards:", card_state.loans_not_yet_counted(card_state.rank_split(17464, parts)[0], parts), "pending")
