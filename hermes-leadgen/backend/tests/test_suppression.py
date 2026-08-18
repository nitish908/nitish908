from app.services.suppression import add_to_suppression_list, is_suppressed


def test_suppression_matches_email(db_session):
    add_to_suppression_list(db_session, value="Person@Example.com", value_type="email")
    db_session.commit()
    assert is_suppressed(db_session, email="person@example.com", website=None) is True
    assert is_suppressed(db_session, email="other@example.com", website=None) is False


def test_suppression_matches_domain(db_session):
    add_to_suppression_list(db_session, value="blocked.example.com", value_type="domain")
    db_session.commit()
    assert is_suppressed(db_session, email=None, website="https://www.blocked.example.com/contact") is True
    assert is_suppressed(db_session, email=None, website="https://allowed.example.com") is False
