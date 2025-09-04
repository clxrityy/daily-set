from app import game


def test_all_cards_length():
    cards = game.all_cards()
    assert len(cards) == 81


def test_is_set_true():
    a = (0,0,0,1)
    b = (1,1,1,1)
    c = (2,2,2,1)
    assert game.is_set(a,b,c)


def test_find_sets_on_daily():
    b = game.daily_board('2025-08-30')
    sets = game.find_sets([tuple(x) for x in b])
    assert isinstance(sets, list)
