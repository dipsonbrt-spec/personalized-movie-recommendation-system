import pytest
from app.api import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

def test_movie_endpoints(client):
    assert client.get("/api/movies/1").status_code == 200
    assert client.get("/api/movies/9999").status_code == 404
    response = client.get("/api/movies/1/similar?limit=3")
    assert response.status_code == 200
    assert len(response.json) == 3

def test_user_rating_recommendation_flow(client):
    created = client.post("/api/users", json={"username": "tester"})
    assert created.status_code == 201
    user_id = created.json["id"]

    rating = client.post(f"/api/users/{user_id}/ratings", json={"movie_id": 1, "rating": 5})
    assert rating.status_code == 201

    recommendations = client.get(f"/api/users/{user_id}/recommendations?limit=5")
    assert recommendations.status_code == 200
    assert len(recommendations.json) == 5
    assert all(item["id"] != 1 for item in recommendations.json)

def test_validation_and_duplicates(client):
    bad = client.post("/api/users", json={"username": ""})
    assert bad.status_code == 400
    first = client.post("/api/users", json={"username": "unique"})
    assert first.status_code == 201
    duplicate = client.post("/api/users", json={"username": "unique"})
    assert duplicate.status_code == 400
