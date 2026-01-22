from pricing import calculate_price


def test_pricing_tiers():
    # high confidence
    p, d, cur = calculate_price("spa", 95.0)
    assert d >= 15.0

    p2, d2, cur2 = calculate_price("spa", 60.0)
    assert d2 == 5.0

    p3, d3, cur3 = calculate_price("unknown", 10.0)
    assert p3 >= 0
