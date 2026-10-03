from flask import Flask, jsonify, request
from .database import init_db, create_user, get_user, get_ratings, upsert_rating
from .recommender import get_movie, search_movies, similar_movies, recommend_for_user


def create_app():
    app = Flask(__name__)
    init_db()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "personalized-movie-recommender"})

    @app.get("/api/movies")
    def movies():
        query = request.args.get("q", "")
        genre = request.args.get("genre", "")
        return jsonify(search_movies(query, genre))

    @app.get("/api/movies/<int:movie_id>")
    def movie(movie_id):
        item = get_movie(movie_id)
        if not item:
            return jsonify({"error": "Movie not found"}), 404
        return jsonify(item)

    @app.get("/api/movies/<int:movie_id>/similar")
    def similar(movie_id):
        try:
            return jsonify(similar_movies(movie_id, limit=min(int(request.args.get("limit", 5)), 20)))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/users")
    def users():
        data = request.get_json(silent=True) or {}
        try:
            user_id = create_user(str(data.get("username", "")))
            return jsonify({"id": user_id, "username": data["username"].strip()}), 201
        except (ValueError, KeyError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/users/<int:user_id>")
    def user(user_id):
        item = get_user(user_id)
        if not item:
            return jsonify({"error": "User not found"}), 404
        return jsonify(item)

    @app.get("/api/users/<int:user_id>/ratings")
    def ratings(user_id):
        if not get_user(user_id):
            return jsonify({"error": "User not found"}), 404
        return jsonify(get_ratings(user_id))

    @app.post("/api/users/<int:user_id>/ratings")
    def rate(user_id):
        data = request.get_json(silent=True) or {}
        try:
            movie_id = int(data["movie_id"])
            rating = float(data["rating"])
            if not get_movie(movie_id):
                raise ValueError("Movie not found")
            upsert_rating(user_id, movie_id, rating)
            return jsonify({"message": "Rating saved"}), 201
        except (KeyError, TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/users/<int:user_id>/recommendations")
    def recommendations(user_id):
        if not get_user(user_id):
            return jsonify({"error": "User not found"}), 404
        ratings_data = get_ratings(user_id)
        genres = request.args.getlist("genre")
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(recommend_for_user(ratings_data, limit=limit, preferred_genres=genres))

    return app
