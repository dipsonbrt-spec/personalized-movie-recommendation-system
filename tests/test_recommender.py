from app.recommender import load_movies, get_movie, search_movies, similar_movies, recommend_for_user

def test_catalog_loads():
    df = load_movies()
    assert len(df) == 30
    assert {"id", "title", "genres", "overview"}.issubset(df.columns)

def test_get_movie():
    movie = get_movie(1)
    assert movie["title"] == "Inception"
    assert get_movie(99999) is None

def test_search_and_genre_filter():
    results = search_movies("Nolan")
    assert any(item["title"] == "Inception" for item in results)
    sci_fi = search_movies(genre="Sci-Fi")
    assert sci_fi
    assert all("Sci-Fi" in item["genres"] for item in sci_fi)

def test_similar_movies_excludes_source():
    results = similar_movies(1, 5)
    assert len(results) == 5
    assert all(item["id"] != 1 for item in results)
    assert results[0]["score"] >= results[-1]["score"]

def test_personalized_recommendations_exclude_rated_movies():
    ratings = [{"movie_id": 1, "rating": 5}, {"movie_id": 2, "rating": 5}]
    results = recommend_for_user(ratings, 10)
    ids = {item["id"] for item in results}
    assert 1 not in ids and 2 not in ids
    assert len(results) == 10

def test_cold_start_genre_preferences():
    results = recommend_for_user([], 10, ["Animation"])
    assert len(results) == 10
    assert "Animation" in results[0]["genres"]
