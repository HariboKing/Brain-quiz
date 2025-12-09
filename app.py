import json
import random
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide")

# ---------- QUIZ STATE (eerst!) ----------
if "score" not in st.session_state:
    st.session_state.score = 0
if "total" not in st.session_state:
    st.session_state.total = 0
if "qid" not in st.session_state:
    st.session_state.qid = 0

# ---------- DATA LADEN ----------
with open("dataset/depth_level_1/medial_basis.regions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

BASE_PATH = data["image"]   # grijze plaat
MASK_PATH = data["mask"]    # gekleurde answers
REGIONS = data["regions"]               # naam -> kleurnaam

# basis en masker laden
base_img = Image.open(BASE_PATH).convert("RGB")
mask_img = Image.open(MASK_PATH).convert("RGB")

W, H = base_img.size
if mask_img.size != (W, H):
    st.error("Mask en basisplaat hebben niet dezelfde afmeting.")
    st.stop()

# ---------- KLEURNAAM -> RGB ----------
COLOR_NAME_TO_RGB = {
    "red": (228, 30, 41),
    "orange": (253, 165, 59),
    "purple": (150, 80, 251),
    "green": (35, 173, 95),
    "blue": (32, 155, 251),
}

# tolerantie-functie
def close_enough(rgb1, rgb2, tol=2):
    return all(abs(a - b) <= tol for a, b in zip(rgb1, rgb2))

# ---------- TARGET INIT + VRAGENLIJSTEN ----------

# Eerste ronde: alle regio's in willekeurige volgorde
if "remaining_questions" not in st.session_state:
    st.session_state.remaining_questions = list(REGIONS.keys())
    random.shuffle(st.session_state.remaining_questions)

# Lijst met vragen die fout zijn gegaan en later terug moeten komen
if "repeat_questions" not in st.session_state:
    st.session_state.repeat_questions = []

# Huidige target
if "target" not in st.session_state:
    # Start met de eerste in de remaining_questions
    st.session_state.target = st.session_state.remaining_questions[0]


def next_question():
    """Schuift door naar de volgende vraag:
       - eerst alle remaining_questions
       - daarna de repeat_questions
    """
    # Verwijder de huidige target uit remaining, als hij daar nog in zit
    if st.session_state.target in st.session_state.remaining_questions:
        st.session_state.remaining_questions.remove(st.session_state.target)

    # Volgende vraag kiezen
    if st.session_state.remaining_questions:
        st.session_state.target = st.session_state.remaining_questions[0]
    elif st.session_state.repeat_questions:
        # Pak de eerstvolgende uit de herhaal-lijst (FIFO)
        st.session_state.target = st.session_state.repeat_questions.pop(0)
    else:
        # Geen vragen meer over
        st.session_state.target = None

# ---------- UI ----------
from streamlit_image_coordinates import streamlit_image_coordinates

st.title("Encephali")
col1, col2 = st.columns([2, 1])
canvas = None

with col1:
    if st.session_state.target is None:
        st.subheader("Klaar!")
        coords = None
    else:
        st.subheader(f"Klik op: **{st.session_state.target}**")

        # Klik-coördinaten ophalen direct op de afbeelding
        coords = streamlit_image_coordinates(
            base_img,
            key=f"img_{st.session_state.qid}",
        )

# ---------- CLICK CHECK ----------
clicked = None
if coords is not None:
    if coords.get("x") is not None and coords.get("y") is not None:
        clicked = (int(coords["x"]), int(coords["y"]))

with col2:
    st.subheader("Resultaat")

    if st.button("Volgende vraag") and st.session_state.target is not None:
        next_question()
        st.session_state.qid += 1
        st.rerun()

    if clicked is not None:
        x, y = clicked

        pixel_rgb = mask_img.getpixel((x, y))  # (R,G,B)

        target_color_name = REGIONS[st.session_state.target]
        target_rgb = COLOR_NAME_TO_RGB[target_color_name]

        st.session_state.total += 1

        if close_enough(pixel_rgb, target_rgb, tol=2):
            st.session_state.score += 1
            st.success("Goed!")
        else:
            # Deze vraag moet aan het eind van de ronde terugkomen
            if st.session_state.target not in st.session_state.repeat_questions:
                st.session_state.repeat_questions.append(st.session_state.target)

            picked_region = "Onbekend / geen regio"
            for region_name, color_name in REGIONS.items():
                rgb = COLOR_NAME_TO_RGB[color_name]
                if close_enough(pixel_rgb, rgb, tol=2):
                    picked_region = region_name
                    break
            st.error(f"Fout. Je klikte op: {picked_region}")

    st.metric("Score", f"{st.session_state.score} / {st.session_state.total}")
       # Als de quiz klaar is, ook percentage tonen
    if st.session_state.target is None and st.session_state.total > 0:
        percentage = round(
            100 * st.session_state.score / st.session_state.total
        )
        st.metric("Percentage goed", f"{percentage}%")
