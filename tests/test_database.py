import pytest
from app.database import create_user, get_user, upsert_rating, get_ratings

def test_user_and_rating_crud():
    user_id = create_user("alice")
    assert get_user(user_id)["username"] == "alice"
    upsert_rating(user_id, 1, 5)
    assert get_ratings(user_id)[0]["movie_id"] == 1
    assert get_ratings(user_id)[0]["rating"] == 5
    upsert_rating(user_id, 1, 4)
    assert get_ratings(user_id)[0]["rating"] == 4

def test_validation():
    with pytest.raises(ValueError):
        create_user(" ")
    user_id = create_user("bob")
    with pytest.raises(ValueError):
        upsert_rating(user_id, 1, 6)
    with pytest.raises(ValueError):
        upsert_rating(999, 1, 5)
