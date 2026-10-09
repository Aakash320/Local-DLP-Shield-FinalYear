from backend.detection.regex_detector import detect_tier0, detect_tier1


def test_aws_key_hit_and_miss():
    hit = detect_tier0("key=AKIAIOSFODNN7EXAMPLE")
    assert [d.detector for d in hit] == ["aws_access_key"]
    assert hit[0].tier == 0
    assert detect_tier0("AKIA is a prefix, not a key") == []


def test_pem_header_hit_and_miss():
    assert (
        detect_tier0("-----BEGIN RSA PRIVATE KEY-----")[0].detector == "pem_private_key"
    )
    assert detect_tier0("-----BEGIN CERTIFICATE-----") == []  # public cert, not a key


def test_db_connection_string_needs_credentials():
    hit = detect_tier0("DATABASE_URL=postgres://admin:s3cret@db.internal:5432/app")
    assert [d.detector for d in hit] == ["db_connection_string"]
    assert detect_tier0("postgres://db.internal:5432/app") == []  # no credentials


def test_email_hit_and_miss():
    hit = detect_tier1("contact priya@example.com now")
    assert [d.category for d in hit] == ["email"]
    assert hit[0].tier == 1
    assert detect_tier1("write to priya at example dot com") == []


def test_phone_hit_and_miss():
    assert [d.category for d in detect_tier1("call 9876543210")] == ["phone"]
    assert [d.category for d in detect_tier1("call +91 98765 43210")] == ["phone"]
    assert detect_tier1("call 1234567890") == []  # Indian mobiles start with 6-9


def test_phone_not_matched_inside_longer_number():
    assert detect_tier1("id 987654321096") == []
