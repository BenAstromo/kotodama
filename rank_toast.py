"""
rank_toast.py
A small toast while reviewing when the Kotodama Japanese Rank goes up.

The rank counts notes with a studied card, so it only rises when a new card
is answered for the first time. Only answers to new cards are checked, so
ordinary reviews cost nothing.
"""

from aqt import gui_hooks
from aqt.utils import tooltip

from . import card_state, rank_data
from .card_state import hook_guard

# Anki card.type values that start counting on this answer (new).
_UNSEEN = (0,)

# unseen: (info, new_rank) of the latest rank-up, shown again on the main
# screen (in the mini widget) after reviewing, in case the toast was missed.
_state = {"deck": None, "count": None, "pending": False, "unseen": None}


def _settings():
    from . import _cfg
    cfg = _cfg()
    return cfg.get("deck_name", ""), bool(cfg.get("ignore_suspended_cards", False))


@hook_guard()
def _set_baseline():
    """Remember the current rank count (on profile open and whenever the
    reviewer starts), so cards added or settings changed in between don't
    trigger a toast."""
    try:
        deck, ignore = _settings()
        _state["deck"]  = deck
        _state["count"] = card_state.rank_count(deck, ignore) if deck else None
    except Exception:
        _state["count"] = None


def _belt_key(info: dict) -> tuple:
    return (info["rank_index"], info["belt_index"], info["degree_index"] or 0)


# A filter hook: whatever happens, Anki gets the answer's ease back unchanged.
@hook_guard(fallback=lambda ease_tuple, reviewer, card: ease_tuple)
def _on_will_answer(ease_tuple, reviewer, card):
    _state["pending"] = False           # stays False if reading the card fails
    _state["pending"] = card.type in _UNSEEN
    return ease_tuple


@hook_guard()
def _on_did_answer(reviewer, card, ease):
    if not _state["pending"]:
        return
    _state["pending"] = False
    deck, ignore = _settings()
    if not deck:
        return
    count = card_state.rank_count(deck, ignore)
    prev  = _state["count"] if _state["deck"] == deck else None
    _state["deck"], _state["count"] = deck, count
    if prev is None or count <= prev:
        return
    before = rank_data.get_rank_info(prev)
    after  = rank_data.get_rank_info(count)
    if _belt_key(after) <= _belt_key(before):
        return
    show_toast(after, new_rank=after["rank_index"] > before["rank_index"])
    from . import mini_widget
    mini_widget.invalidate_cache()


def peek_unseen():
    """The latest rank-up for the main-screen banner, or None. It stays
    until dismiss_unseen(): the banner's ✕, opening the add-on from the
    widget, or starting the next review session."""
    return _state["unseen"]


def dismiss_unseen():
    _state["unseen"] = None


def show_toast(info: dict, new_rank: bool, parent=None):
    """Also called by the Overview's debug "Test … toast" buttons.
    During review, parent=None puts it at the bottom-left of Anki's main
    window (the review screen)."""
    _state["unseen"] = (info, new_rank)
    head = "New rank!" if new_rank else "Belt up!"
    tooltip(
        f"<div style='font-size:14px;'><b style='color:{rank_data.MAX_RANK_FILL_COLOR};'>"
        f"⬆ {head}</b><br>"
        # Plain text colours: some rank colours (Nihonjin black) are
        # unreadable on a tooltip background.
        f"<b>{info['rank_name_jp']}</b> {info['rank_name_en']} · "
        f"<b>{info['belt_display_name']} Belt</b><br>"
        f"<span style='color:#aaa; font-size:11px;'>{info['count']:,} learned words</span></div>",
        period=5000,
        parent=parent,
    )


@hook_guard()
def _on_state_change(new_state, old_state):
    if new_state == "review":
        _set_baseline()
        dismiss_unseen()   # a new session: the old banner has had its chance
    elif new_state == "deckBrowser" and _state["unseen"]:
        # The mini widget shows the reminder; without it, repeat the toast.
        from . import _cfg
        if not _cfg().get("mini_widget_enabled", True):
            info, new_rank = _state["unseen"]
            show_toast(info, new_rank)
            dismiss_unseen()


def setup():
    gui_hooks.profile_did_open.append(_set_baseline)
    gui_hooks.state_did_change.append(_on_state_change)
    gui_hooks.reviewer_will_answer_card.append(_on_will_answer)
    gui_hooks.reviewer_did_answer_card.append(_on_did_answer)
