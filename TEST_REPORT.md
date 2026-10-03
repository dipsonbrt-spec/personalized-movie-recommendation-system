# Test Report

## Executed successfully

- Python syntax compilation for application and tests.
- Movie catalog loading: 30 movies.
- Movie lookup and missing-movie handling.
- Search and genre filtering.
- Similar-movie generation and exclusion of the source movie.
- Personalized recommendations exclude already-rated movies.
- Cold-start recommendations honor selected genres.
- Recommendation explanations are generated.
- SQLite user creation.
- SQLite rating insert/update behavior.
- Rating validation.

## Full pytest/API execution note

The execution environment used to assemble this archive did not have Flask or Streamlit installed, and outbound package installation was unavailable. Therefore `pytest -q` could not be executed here because the Flask-dependent API test module cannot import Flask.

The test suite is included in the project and should be run after installing `requirements.txt` in the user's local virtual environment:

```bash
pip install -r requirements.txt
pytest -q
```

This is reported explicitly instead of claiming that an unavailable dependency was tested.
