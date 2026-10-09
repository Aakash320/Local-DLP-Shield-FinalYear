from backend.detection.entropy_detector import detect, shannon_entropy


def test_entropy_values_ordered():
    assert shannon_entropy("aaaaaaaa") == 0.0
    assert shannon_entropy("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY") > 4.5


def test_random_looking_secret_hit():
    hits = detect("secret=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    assert len(hits) == 1
    assert hits[0].tier == 1 and hits[0].category == "secret"


def test_long_but_ordinary_identifier_is_a_clean_miss():
    assert detect("internationalization_configuration_manager") == []


def test_short_tokens_are_ignored():
    assert detect("x7Qp9zLk") == []


def test_threshold_and_min_length_are_parameters():
    text = "internationalization_configuration_manager"
    assert detect(text, threshold=3.0)  # loosen the threshold -> now it fires
    assert detect("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", min_length=50) == []
