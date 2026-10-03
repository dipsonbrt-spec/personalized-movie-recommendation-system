# Personalized Movie Recommendation System

A production-style starter application built with **Python, Flask, Streamlit, SQLite, pandas, and scikit-learn**.

## Architecture

- `app/recommender.py` — TF-IDF content-based recommendation engine.
- `app/database.py` — SQLite persistence for users and ratings.
- `app/api.py` — Flask REST API.
- `streamlit_app.py` — Streamlit web interface.
- `data/movies.csv` — bundled movie catalog; no external API key is required.
- `tests/` — automated unit/API tests.

The Streamlit application can run completely standalone using the same recommendation engine. Flask is included as a clean REST API layer and can be deployed separately when an API endpoint is required.

## Features

- Create/select a user profile.
- Rate movies from 1–5 stars.
- Personalized recommendations based on the user's ratings.
- Cold-start recommendations based on selected genres.
- "Because you liked" explanations.
- Similar-movie recommendations.
- Search/filter the catalog.
- Flask JSON API for movies, ratings, recommendations, and similar movies.
- SQLite persistence.
- Automated tests.

## 1. Local setup

You said your virtual environment is already created, so activate it and run:

```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize the database:

```bash
python -m app.database
```

### Start Streamlit

```bash
streamlit run streamlit_app.py
```

Open the URL shown by Streamlit, normally `http://localhost:8501`.

### Start Flask API

Open a second terminal, activate the same environment, then:

```bash
python run_flask.py
```

Flask runs on `http://127.0.0.1:5000`.

Useful endpoints:

```text
GET  /api/health
GET  /api/movies
GET  /api/movies/<movie_id>
GET  /api/movies/<movie_id>/similar
POST /api/users
POST /api/users/<user_id>/ratings
GET  /api/users/<user_id>/ratings
GET  /api/users/<user_id>/recommendations
```

Example rating request:

```json
{
  "movie_id": 1,
  "rating": 5
}
```

## 2. Running tests

From the project root:

```bash
pytest -q
```

The tests cover database initialization, movie loading, recommendation behavior, Flask endpoints, validation, and cold-start behavior.

## 3. Streamlit Community Cloud deployment

This project is designed so Streamlit can run without Flask. That is intentional: Streamlit Community Cloud runs the UI process, while the recommendation engine and SQLite database are used directly by the Streamlit app.

### GitHub

1. Create a GitHub repository.
2. Upload all project files.
3. In Streamlit Community Cloud, create a new app.
4. Select the repository and branch.
5. Set the main file to:

```text
streamlit_app.py
```

6. Deploy.

No secrets are required for the bundled dataset.

### Important persistence note

SQLite is suitable for local development and simple demos. Streamlit Community Cloud's local filesystem should **not** be treated as permanent production storage. For a public multi-user deployment, replace `app/database.py` with PostgreSQL/Supabase/another hosted database and use a persistent backend.

## 4. Deploying Flask separately

For a hosted API, use a Python web service such as Render, Railway, Fly.io, or another WSGI-compatible platform.

The repository already contains:

- `Procfile`
- `render.yaml`
- `runtime.txt`

A typical WSGI command is:

```bash
gunicorn run_flask:app
```

If your hosted Flask API URL is later available, the Streamlit app can be extended to consume that API. The current Streamlit app intentionally uses the engine locally so it remains deployable as a single Streamlit application.

## Recommendation approach

The recommender uses TF-IDF vectors over movie metadata (`genres`, `keywords`, `director`, `cast`, and `overview`) and cosine similarity. A user's profile vector is built from movies they rated, weighting each liked movie by how strongly the rating is above neutral. Already-rated movies are excluded.

This is a content-based recommender, so it does not require millions of users or an external ML service. For a larger production system, the next step would usually be a hybrid model combining collaborative filtering with content features and a persistent feature/model store.
