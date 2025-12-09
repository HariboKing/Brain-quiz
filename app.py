import json
import random
import streamlit as st
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(layout="wide")

# ---------- QUIZ STATE (eerst!) ----------
if "phase" not in st.session_state:
    st.session_state.phase = "click"   # "click" of "followup"

if "last_correct_region" not in st.session_state:
    st.session_state.last_correct_region = None

if "followup_answers" not in st.session_state:
    st.session_state.followup_answers = {}  # region -> list answers

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
REGIONS = data["regions"]   # naam -> kleurnaam

base_img = Image.open(BASE_PATH).convert("RGB")
mask_img = Image.open(MASK_PATH).convert("RGB")

W, H = base_img.size
if mask_img.size != (W, H):
    st.error("Mask en basisplaat hebben niet dezelfde afmeting.")
    st.stop()

# ---------- KLEURNAAM -> RGB ----------
COLOR_NAME_TO_RGB = {
    "red":    (228, 30, 41),
    "orange": (253, 165, 59),
    "purple": (150, 80, 251),
    "green":  (35, 173, 95),
    "blue":   (32, 155, 251),
}

def close_enough(rgb1, rgb2, tol=2):
    return all(abs(a - b) <= tol for a, b in zip(rgb1, rgb2))

# ---------- VRAAGBANK PER REGIO ----------
FOLLOWUP_QUESTIONS = {
    "Myelencephalon": [
        {
            "q": "Wat is de functie van het Myelencephalon?",
            "keywords": ["ademhaling", "hartslag", "autonoom", "vitale functies", "reflexen"]
        },
        {
            "q": "Uit welke delen bestaat het Myelencephalon?",
            "keywords": ["medulla", "oblongata", "verlengde merg"]
        },
    ],
}

# ---------- TARGET INIT + VRAGENLIJSTEN ----------
if "remaining_questions" not in st.session_state:
    st.session_state.remaining_questions = list(REGIONS.keys())
    random.shuffle(st.session_state.remaining_questions)

if "repeat_questions" not in st.session_state:
    st.session_state.repeat_questions = []

if "target" not in st.session_state:
    st.session_state.target = st.session_state.remaining_questions[0]

def next_question():
    # verwijder huidige uit remaining
    if st.session_state.target in st.session_state.remaining_questions:
        st.session_state.remaining_questions.remove(st.session_state.target)

    if st.session_state.remaining_questions:
        st.session_state.target = st.session_state.remaining_questions[0]
    elif st.session_state.repeat_questions:
        st.session_state.target = st.session_state.repeat_questions.pop(0)
    else:
        st.session_state.target = None

# ---------- UI ----------
st.title("Encephali")
col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.target is None:
        st.subheader("Klaar!")
        coords = None
    else:
        st.subheader(f"Klik op: **{st.session_state.target}**")
        coords = streamlit_image_coordinates(
            base_img,
            key=f"img_{st.session_state.qid}",
        )

# ---------- CLICK CHECK ----------
clicked = None
if coords is not None and coords.get("x") is not None and coords.get("y") is not None:
    clicked = (int(coords["x"]), int(coords["y"]))

with col2:
    st.subheader("Resultaat")

    # ---------- FOLLOW-UP UI ----------
    if st.session_state.phase == "followup":
        region = st.session_state.last_correct_region
        st.subheader(f"Vragen over: {region}")

        user_answers = []
        all_ok = True

        for i, item in enumerate(FOLLOWUP_QUESTIONS.get(region, []), start=1):
            ans = st.text_input(item["q"], key=f"followup_{st.session_state.qid}_{i}")
            user_answers.append(ans)

            if ans.strip():
                ans_low = ans.lower()
                if not any(k in ans_low for k in item["keywords"]):
                    all_ok = False
            else:
                all_ok = False

        colA, colB = st.columns(2)

        with colA:
            if st.button("Check antwoorden"):
                if all_ok:
                    st.success("Follow-up goed!")
                else:
                    st.warning("Niet helemaal. Probeer nog eens.")

        with colB:
            if st.button("Volgende regio"):
                st.session_state.followup_answers[region] = user_answers
                st.session_state.phase = "click"
                next_question()
                st.session_state.qid += 1
                st.rerun()

    # ---------- CLICK-FASE ----------
    if st.session_state.phase == "click":

        if st.button("Volgende vraag") and st.session_state.target is not None:
            next_question()
            st.session_state.qid += 1
            st.rerun()

        if clicked is not None and st.session_state.target is not None:
            x, y = clicked

            pixel_rgb = mask_img.getpixel((x, y))
            target_color_name = REGIONS[st.session_state.target]
            target_rgb = COLOR_NAME_TO_RGB[target_color_name]

            st.session_state.total += 1

            if close_enough(pixel_rgb, target_rgb, tol=2):
                st.session_state.score += 1
                st.success("Goed!")

                region = st.session_state.target
                if region in FOLLOWUP_QUESTIONS:
                    st.session_state.phase = "followup"
                    st.session_state.last_correct_region = region
                    st.rerun()

            else:
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

    if st.session_state.target is None and st.session_state.total > 0:
        percentage = round(100 * st.session_state.score / st.session_state.total)
        st.metric("Percentage goed", f"{percentage}%")
