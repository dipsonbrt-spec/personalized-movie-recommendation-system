import streamlit as st
from app.database import init_db, create_user, get_user, get_ratings, upsert_rating
from app.recommender import load_movies, search_movies, similar_movies, recommend_for_user

st.set_page_config(page_title="Personalized Movie Recommendation System", page_icon="🎬", layout="wide")
init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

st.title("My Personalized Movie Recommender")
st.caption("Rate movies you know, then discover movies matched to your taste.")

with st.sidebar:
    st.header("Profile")
    username = st.text_input("Username", value=st.session_state.username or "", placeholder="e.g. dipson")
    if st.button("Create profile", use_container_width=True):
        try:
            user_id = create_user(username)
            st.session_state.user_id = user_id
            st.session_state.username = username.strip()
            st.success("Profile created!")
        except ValueError as exc:
            st.error(str(exc))

    if st.session_state.user_id:
        st.info(f"Signed in as **{st.session_state.username}**")

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
    q = st.text_input("Search title, actor, director, genre, or keyword", key="catalog_search")
    genre = st.selectbox("Genre", ["All"] + sorted({g for value in movies["genres"] for g in value.split("|")}))
    catalog = search_movies(q, genre)
    st.dataframe(catalog, hide_index=True, use_container_width=True)
