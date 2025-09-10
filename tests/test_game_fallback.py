from app import game


def test_daily_board_fallback_still_returns_set():
    # Choose a size and date; function ensures a set exists; fallback path covered by loop cap
    board = game.daily_board('2099-02-02', size=12)
    assert isinstance(board, list) and len(board) == 12
    # Verify at least one set exists
    from app.game import find_sets
    sets = find_sets([tuple(c) for c in board])
    assert len(sets) >= 1
