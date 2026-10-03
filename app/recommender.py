from functools import lru_cache
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .config import MOVIES_PATH

FEATURE_COLUMNS = ["genres", "director", "cast", "keywords", "overview"]

@lru_cache(maxsize=1)
def load_movies():
    df = pd.read_csv(MOVIES_PATH)
    df["id"] = df["id"].astype(int)
    df["year"] = df["year"].astype(int)
    df["runtime"] = df["runtime"].astype(int)
    df["metadata"] = df[FEATURE_COLUMNS].fillna("").agg(" ".join, axis=1).str.lower()
    return df

@lru_cache(maxsize=1)
def get_vectorizer_and_matrix():
    df = load_movies()
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(df["metadata"])
    return vectorizer, matrix

def _row_index(movie_id: int):
    matches = np.flatnonzero(load_movies()["id"].to_numpy() == int(movie_id))
    return int(matches[0]) if len(matches) else None

def get_movie(movie_id: int):
    idx = _row_index(movie_id)
    if idx is None:
        return None
    row = load_movies().iloc[idx]
    return row.drop(labels=["metadata"]).to_dict()

def search_movies(query: str = "", genre: str = ""):
    df = load_movies()
    result = df
    if query.strip():
        q = query.strip().lower()
        mask = result["title"].str.lower().str.contains(q, regex=False) | result["metadata"].str.contains(q, regex=False)
        result = result[mask]
    if genre and genre != "All":
        result = result[result["genres"].str.contains(genre, case=False, regex=False)]
    return result.drop(columns=["metadata"]).to_dict("records")

def similar_movies(movie_id: int, limit: int = 5):
    idx = _row_index(movie_id)
    if idx is None:
        raise ValueError("Movie not found")
    _, matrix = get_vectorizer_and_matrix()
    scores = cosine_similarity(matrix[idx], matrix).ravel()
    order = np.argsort(-scores)
    output = []
    for i in order:
        if i == idx:
            continue
        row = load_movies().iloc[i].drop(labels=["metadata"]).to_dict()
        row["score"] = round(float(scores[i]), 4)
        output.append(row)
        if len(output) >= limit:
            break
    return output

def recommend_for_user(ratings: list[dict], limit: int = 10, preferred_genres: list[str] | None = None):
    df = load_movies()
    _, matrix = get_vectorizer_and_matrix()
    rated_ids = {int(r["movie_id"]) for r in ratings}

    if ratings:
        profile = np.zeros((1, matrix.shape[1]))
        total_weight = 0.0
        for item in ratings:
            idx = _row_index(int(item["movie_id"]))
            if idx is None:
                continue
            rating = float(item["rating"])
            # Center ratings around neutral 3. A 5-star rating strongly pulls toward a movie;
            # a 1-star rating pushes away from it.
            weight = rating - 3.0
            profile += matrix[idx].toarray() * weight
            total_weight += abs(weight)
        if total_weight > 0:
            profile /= total_weight
            scores = cosine_similarity(profile, matrix).ravel()
        else:
            scores = np.zeros(len(df))
    else:
        scores = np.zeros(len(df))

    # Cold start / extra genre preference boost.
    if preferred_genres:
        selected = [g.lower() for g in preferred_genres]
        for i, genres in enumerate(df["genres"]):
            genre_set = {g.strip().lower() for g in genres.split("|")}
            scores[i] += 0.15 * sum(g in genre_set for g in selected)

    order = np.argsort(-scores)
    result = []
    positive_rated = []
    for item in ratings:
        if float(item["rating"]) >= 4:
            idx = _row_index(int(item["movie_id"]))
            if idx is not None:
                positive_rated.append((idx, float(item["rating"])))

    for i in order:
        movie_id = int(df.iloc[i]["id"])
        if movie_id in rated_ids:
            continue
        row = df.iloc[i].drop(labels=["metadata"]).to_dict()
        row["score"] = round(float(scores[i]), 4)
        if positive_rated:
            rated_indices = [idx for idx, _ in positive_rated]
            similarities = cosine_similarity(matrix[i], matrix[rated_indices]).ravel()
            best_idx = rated_indices[int(np.argmax(similarities))]
            row["reason"] = f"Similar to {df.iloc[best_idx]['title']}"
        elif preferred_genres:
            row["reason"] = "Matches your selected genre preferences"
        else:
            row["reason"] = "A catalog recommendation based on your current profile"
        result.append(row)
        if len(result) >= limit:
            break
    return result
