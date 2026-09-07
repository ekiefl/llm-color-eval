from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from color_guesser.db import connect, insert_description, insert_guess
from color_guesser.describer import build_describer
from color_guesser.guesser import build_guesser
from color_guesser.llm import GROQ_BASE_URL, list_model_names, resolve_model
from color_guesser.metrics import delta_e, dialed_score

load_dotenv()

DB_PATH = Path("data/results.db")


@st.cache_data
def model_names(base_url: str, api_key_env: str) -> list[str]:
    """Fetch the endpoint's model list once per session.

    Args:
        base_url: Base URL of the endpoint.
        api_key_env: Name of the environment variable holding the API key.

    Returns:
        Model names in sorted order.
    """
    return list_model_names(base_url, api_key_env)


def comparison_square(source_hex: str, guessed_hex: str) -> str:
    """Render two colors as a diagonally split square.

    The top-left triangle is the source color and the bottom-right triangle is
    the guess, sharing a diagonal edge so differences are directly visible.

    Args:
        source_hex: The source color.
        guessed_hex: The guessed color.

    Returns:
        An SVG fragment.
    """
    return (
        '<svg width="320" height="320" viewBox="0 0 100 100">'
        f'<polygon points="0,0 100,0 0,100" fill="{source_hex}"/>'
        f'<polygon points="100,0 100,100 0,100" fill="{guessed_hex}"/>'
        "</svg>"
    )


st.set_page_config(page_title="Color Guesser", page_icon="🎨")
st.title("Color Guesser")

with st.sidebar:
    base_url = st.text_input("Endpoint", GROQ_BASE_URL)
    api_key_env = st.text_input("API key env var", "GROQ_KEY")

names = model_names(base_url, api_key_env)
hex_code = st.color_picker("Color", "#3fa76e").lower()
describer_name = st.selectbox("Describer", names)
guesser_name = st.selectbox("Guesser", names)
max_words = st.slider("Word budget", 5, 60, 30)

if st.button("Run", type="primary"):
    describer = build_describer(resolve_model(describer_name, base_url, api_key_env), max_words)
    guesser = build_guesser(resolve_model(guesser_name, base_url, api_key_env))
    with st.spinner("Describing..."):
        description = describer.run_sync(hex_code).output
    with st.spinner("Guessing..."):
        guess = guesser.run_sync(description).output
    score = dialed_score(hex_code, guess.hex_code)
    distance = delta_e(hex_code, guess.hex_code)
    conn = connect(DB_PATH)
    description_id = insert_description(conn, hex_code, describer_name, max_words, description)
    insert_guess(conn, description_id, guesser_name, guess.hex_code, score, distance)
    conn.close()
    st.markdown(f"> {description}")
    st.markdown(comparison_square(hex_code, guess.hex_code), unsafe_allow_html=True)
    st.caption(f"top left: source {hex_code} · bottom right: guess {guess.hex_code}")
    score_col, delta_col = st.columns(2)
    score_col.metric("Score", f"{score:.2f} / 10")
    delta_col.metric("Delta E", f"{distance:.2f}")
