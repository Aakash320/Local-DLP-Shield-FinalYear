from backend.detection.keyword_detector import detect


def test_keyword_hit_case_insensitive():
    hits = detect("This memo is CONFIDENTIAL.")
    assert [d.category for d in hits] == ["confidential_keyword"]
    assert hits[0].tier == 1


def test_keyword_clean_miss_word_boundary():
    assert detect("The confidentiality agreement is attached.") == []


def test_custom_keyword_list():
    assert detect("Project Falcon roadmap", keywords=["project falcon"])
    assert detect("Project Falcon roadmap", keywords=[]) == []
