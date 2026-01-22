from pricing import calculate_price


def test_pricing_inr_for_indian_city():
    price, discount, currency = calculate_price("facial", 76.0, None, location="vijayawada")
    assert currency == "INR"
    # base 27, discount 10% -> 24.3 USD -> INR ~ 24.3 * 82
    assert price == round(24.3 * 82.0, 2)
