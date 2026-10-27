exec(open("loans.py", encoding="utf-8").read().split("lists = ")[0])
rows = freq_data.load()
loan_ranks = [i + 1 for i, r in enumerate(rows) if freq_data.is_english_loanword(r[0], r[1])]
print("English loanwords in the top 20,000:", len(loan_ranks), "| examples:", [rows[i - 1][0] for i in loan_ranks[:12]])
import bisect
def L(c): return bisect.bisect_right(loan_ranks, c)
print("cards → loanwords unlocked → rank")
for c in (100, 500, 1000, 2000, 3160, 5000, 8000, 10000, 13800, 16000, 17000, 17500, 18000):
    print(f"  {c:>6,} → {L(c):>5,} → {c + L(c):>6,}")
c = next(c for c in range(15000, 20001) if c + L(c) >= 20000)
print("cards needed for 20,000 with the schedule:", c)
print("\n-- owner's schedule: a loanword at rank r unlocks at r minus the loanwords already unlocked --")
thr = [r - i for i, r in enumerate(loan_ranks)]          # non-decreasing
def L2(c): return bisect.bisect_right(thr, c)
for c in (100, 500, 1000, 2000, 3160, 5000, 8000, 10000, 13800, 15000, 16000, 17000, 17464):
    print(f"  {c:>6,} → {L2(c):>5,} → {c + L2(c):>6,}")
c = next(c for c in range(14000, 20001) if c + L2(c) >= 20000)
print("cards needed for 20,000:", c, "| all marked at once would need:", 20000 - len(loan_ranks))
print("share card / Nakama today: grep")
