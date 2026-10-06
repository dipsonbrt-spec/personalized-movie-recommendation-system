import pandas as pd
from app.database import add_movies
from app.recommender import refresh_movies
import streamlit as st
from app.database import (
    init_db, create_user, authenticate_user, get_user, get_ratings, upsert_rating,
)
from app.recommender import load_movies, search_movies, similar_movies, recommend_for_user

st.set_page_config(page_title="Personalized Movie Recommendation System", page_icon="🎬", layout="wide")
init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None


def _login_state(user_id, username):
    st.session_state.user_id = user_id
    st.session_state.username = username


def _logout():
    st.session_state.user_id = None
    st.session_state.username = None


st.title("My Personalized Movie Recommender")
st.caption("Rate movies you know, then discover movies matched to your taste.")

with st.sidebar:
    st.header("Profile")

    if st.session_state.user_id:
        st.info(f"Signed in as **{st.session_state.username}**")
        if st.button("Log out", use_container_width=True):
            _logout()
            st.rerun()
    else:
        username = st.text_input("Username", placeholder="e.g. dipson")
        password = st.text_input("Password", type="password", placeholder="At least 6 characters")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Create profile", use_container_width=True):
                try:
                    user_id = create_user(username, password)
                    _login_state(user_id, username.strip())
                    st.success("Profile created!")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        with col_b:
            if st.button("Log in", use_container_width=True):
                try:
                    user = authenticate_user(username, password)
                    _login_state(user["id"], user["username"])
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.divider()
    all_genres = sorted({g for value in load_movies()["genres"] for g in value.split("|")})
    preferred_genres = st.multiselect("Optional genre preferences", all_genres)
    st.caption("Genre preferences help when you have few or no ratings.")

movies = load_movies()
ratings = get_ratings(st.session_state.user_id) if st.session_state.user_id else []
rated_map = {int(r["movie_id"]): float(r["rating"]) for r in ratings}

home, rate_tab, similar_tab, catalog_tab = st.tabs(["Recommendations", "Rate Movies", "Similar Movies", "Catalog"])

with home:
    if not st.session_state.user_id:
        st.info("Create a profile in the sidebar to save ratings and get personalized recommendations.")
        st.subheader("Popular starter picks")
        st.dataframe(movies[["title", "year", "genres", "director"]].head(8), hide_index=True, use_container_width=True)
    else:
        st.subheader("Recommended for you")
        recs = recommend_for_user(ratings, limit=10, preferred_genres=preferred_genres)
        if not ratings and not preferred_genres:
            st.info("Rate a few movies or select some genres to make recommendations more personalized.")
        for movie in recs:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {movie['title']} ({movie['year']})")
                    st.write(f"**Genres:** {movie['genres'].replace('|', ', ')}")
                    st.write(f"**Director:** {movie['director']}")
                    st.write(movie['overview'])
                    st.caption(f"{movie['reason']}")
                with col2:
                    st.metric("Match", f"{max(0, movie['score']) * 100:.0f}%")
                    if st.button("Why / similar", key=f"why_{movie['id']}"):
                        sims = similar_movies(int(movie["id"]), limit=3)
                        st.write("Similar titles:")
                        for sim in sims:
                            st.write(f"• {sim['title']}")

with rate_tab:
    st.subheader("Rate movies")
    query = st.text_input("Search movies", key="rating_search")
    results = search_movies(query)[:15]
    if not results:
        st.warning("No movies found.")
    for movie in results:
        current = rated_map.get(int(movie["id"]), 0.0)
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            st.write(f"**{movie['title']}** ({movie['year']})")
            st.caption(movie["genres"].replace("|", " • "))
        with col2:
            value = st.slider("Rating", 1.0, 5.0, current if current else 3.0, 0.5, key=f"rating_{movie['id']}")
        with col3:
            if st.button("Save", key=f"save_{movie['id']}"):
                if not st.session_state.user_id:
                    st.error("Create a profile first.")
                else:
                    upsert_rating(st.session_state.user_id, int(movie["id"]), float(value))
                    st.success("Saved")
                    st.rerun()

with similar_tab:
    st.subheader("Find similar movies")
    selected_title = st.selectbox("Movie", movies["title"].tolist())
    selected_id = int(movies.loc[movies["title"] == selected_title, "id"].iloc[0])
    selected = movies.loc[movies["id"] == selected_id].iloc[0]
    st.write(selected["overview"])
    for movie in similar_movies(selected_id, limit=6):
        st.markdown(f"**{movie['title']}** — {movie['genres'].replace('|', ', ')} — similarity {movie['score']:.2f}")

with catalog_tab:
    st.subheader("Movie catalog")
    st.caption(f"{len(movies)} movies currently in the catalog.")

    if st.session_state.get("import_message"):
        kind, text = st.session_state.pop("import_message")
        (st.success if kind == "success" else st.error)(text)

    uploaded = st.file_uploader(
        "Upload a movies CSV",
        type=["csv"],
        help="Required column: title. Optional: year, genres (A|B|C), director, cast, keywords, overview, runtime.",
    )
    if uploaded is not None:
        signature = (uploaded.name, uploaded.size)
        if st.session_state.get("last_import") != signature:
            st.session_state.last_import = signature
            try:
                df = pd.read_csv(uploaded)
                df.columns = [c.strip().lower() for c in df.columns]
                if "title" not in df.columns:
                    raise ValueError("The CSV must have a 'title' column.")
                added, skipped = add_movies(df.to_dict("records"))
                refresh_movies()
                st.session_state.import_message = (
                    "success", f"Added {added} new movies. Skipped {skipped} (duplicates or missing title)."
                )
            except Exception as exc:
                st.session_state.import_message = ("error", f"Could not import the file: {exc}")
            st.rerun()