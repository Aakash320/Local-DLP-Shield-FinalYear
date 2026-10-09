from backend.detection.checksum_detector import (
    detect,
    luhn_valid,
    verhoeff_check_digit,
    verhoeff_valid,
)


def test_luhn_valid_and_invalid():
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")


def test_verhoeff_known_example():
    assert verhoeff_valid("2363")  # classic textbook example
    assert verhoeff_check_digit("236") == "3"
    assert not verhoeff_valid("2364")


def test_card_hit_with_separators():
    hits = detect("pay with 4111 1111 1111 1111 please")
    assert [d.category for d in hits] == ["credit_card"]
    assert all(d.tier == 0 for d in hits)


def test_card_miss_fails_luhn():
    assert detect("order id 4111 1111 1111 1112") == []


def test_aadhaar_hit_plain_and_grouped():
    assert [d.category for d in detect("id 234567890124")] == ["aadhaar"]
    assert [d.category for d in detect("id 2345 6789 0124")] == ["aadhaar"]


def test_aadhaar_miss_fails_verhoeff():
    # right shape, wrong checksum: exactly the order-ID / phone-number case
    assert detect("ref 234567890125") == []


def test_card_is_not_misread_as_aadhaar():
    cats = [d.category for d in detect("4111 1111 1111 1111")]
    assert cats == ["credit_card"]


def test_pan_hit_and_miss():
    assert [d.category for d in detect("PAN ABCPE1234F")] == ["pan"]
    assert detect("code ABCZE1234F") == []  # 4th letter Z is not a valid holder type
    assert detect("abcpe1234f") == []  # PAN is uppercase
