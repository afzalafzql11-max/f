import streamlit as st
import sqlite3
import cv2
import numpy as np
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Missing Child System", layout="centered")

DB = "database.db"
DATASET = "dataset"
UPLOAD = "uploads"

os.makedirs(DATASET, exist_ok=True)
os.makedirs(UPLOAD, exist_ok=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS children(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    place TEXT,
    image_path TEXT
)
""")

conn.commit()

# ---------------- FACE ----------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

recognizer = cv2.face.LBPHFaceRecognizer_create()

# ---------------- FUNCTIONS ----------------

def extract_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return None

    x, y, w, h = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))

    # Improve quality
    face = cv2.equalizeHist(face)

    return face

def generate_variants(face):
    variants = []

    variants.append(face)
    variants.append(cv2.GaussianBlur(face, (5,5), 0))
    variants.append(cv2.convertScaleAbs(face, alpha=1.2, beta=20))

    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    variants.append(cv2.filter2D(face, -1, kernel))

    return variants

def train_model():
    faces = []
    labels = []

    rows = c.execute("SELECT id,image_path FROM children").fetchall()

    for row in rows:
        img = cv2.imread(row[1], 0)
        if img is None:
            continue
        faces.append(img)
        labels.append(row[0])

    if len(faces) > 0:
        recognizer.train(faces, np.array(labels))

def match_face(img):
    face = extract_face(img)

    if face is None:
        return None, None

    variants = generate_variants(face)

    best_conf = 999
    best_label = None

    for v in variants:
        try:
            label, conf = recognizer.predict(v)
            if conf < best_conf:
                best_conf = conf
                best_label = label
        except:
            pass

    return best_label, best_conf

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.admin = False

# ---------------- AUTH ----------------

def signup():
    st.title("Signup")

    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        c.execute("INSERT INTO users(name,email,password) VALUES (?,?,?)",
                  (name, email, password))
        conn.commit()
        st.success("Account created!")

def login():
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # ADMIN LOGIN
        if email == "admin@123" and password == "ths343$":
            st.session_state.logged_in = True
            st.session_state.admin = True
            st.success("Admin Logged In")
            return

        user = c.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        if user:
            st.session_state.logged_in = True
            st.success("Login Successful")
        else:
            st.error("Invalid Credentials")

# ---------------- DASHBOARD ----------------

def dashboard():
    st.title("Dashboard")

    rows = c.execute("SELECT * FROM children").fetchall()

    if len(rows) == 0:
        st.info("No data available")
        return

    for row in rows:
        st.write(f"👤 {row[1]} | Age: {row[2]} | 📍 {row[3]}")

        if st.session_state.admin:
            if st.button(f"Delete ID {row[0]}"):
                c.execute("DELETE FROM children WHERE id=?", (row[0],))
                conn.commit()
                st.warning("Deleted")
                st.rerun()

# ---------------- UPLOAD ----------------

def upload_child():
    st.title("Upload Missing Child")

    name = st.text_input("Name")
    age = st.number_input("Age", 1, 100)
    place = st.text_input("Place and contact details")

    img_file = st.file_uploader("Upload Image")

    if st.button("Upload"):
        if img_file is None:
            st.error("Upload image first")
            return

        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)

        face = extract_face(img)

        if face is None:
            st.error("No face detected")
            return

        c.execute("INSERT INTO children(name,age,place,image_path) VALUES (?,?,?,?)",
                  (name, age, place, ""))
        conn.commit()

        child_id = c.lastrowid

        path = os.path.join(DATASET, f"{child_id}.jpg")
        cv2.imwrite(path, face)

        c.execute("UPDATE children SET image_path=? WHERE id=?",
                  (path, child_id))
        conn.commit()

        train_model()

        st.success("Child Added Successfully")

# ---------------- CROSSCHECK ----------------

def crosscheck():
    st.title("Cross Check")

    img_file = st.file_uploader("Upload Image to Match")

    if st.button("Check"):
        if img_file is None:
            st.error("Upload image first")
            return

        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)

        train_model()

        label, conf = match_face(img)

        if label is None:
            st.error("No face detected")
            return

        if conf < 60:
            child = c.execute("SELECT * FROM children WHERE id=?",
                              (label,)).fetchone()
            st.success("✅ MATCH FOUND")
            st.write(child)

        elif conf < 85:
            child = c.execute("SELECT * FROM children WHERE id=?",
                              (label,)).fetchone()
            st.warning("⚠ MATCH FOUND (AGE VARIATION)")
            st.write(child)

        else:
            st.error("❌ Not Found")

# ---------------- MAIN ----------------

menu = ["Login", "Signup"]

if st.session_state.logged_in:
    menu = ["Dashboard", "Upload", "CrossCheck"]

choice = st.sidebar.selectbox("Menu", menu)

if not st.session_state.logged_in:
    if choice == "Signup":
        signup()
    else:
        login()
else:
    if choice == "Dashboard":
        dashboard()
    elif choice == "Upload":
        upload_child()
    elif choice == "CrossCheck":
        crosscheck()
