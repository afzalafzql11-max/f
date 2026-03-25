import streamlit as st
import sqlite3
import os
from deepface import DeepFace

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Missing Child System", layout="centered")

DB = "database.db"
UPLOAD = "uploads"
os.makedirs(UPLOAD, exist_ok=True)

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(email TEXT, password TEXT)")

    c.execute("""
    CREATE TABLE IF NOT EXISTS children(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        location TEXT,
        contact TEXT,
        image TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- AUTH ----------------
def signup(email, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO users VALUES(?,?)", (email, password))
    conn.commit()
    conn.close()

def login(email, password):
    # ADMIN LOGIN
    if email == "admin@123" and password == "ths343$":
        return "admin"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = c.fetchone()
    conn.close()

    if user:
        return "user"
    return None

# ---------------- CHILD ----------------
def save_child(name, age, location, contact, image):
    path = os.path.join(UPLOAD, image.name)

    with open(path, "wb") as f:
        f.write(image.getbuffer())

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO children(name,age,location,contact,image)
    VALUES(?,?,?,?,?)
    """, (name, age, location, contact, path))

    conn.commit()
    conn.close()

def get_children():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM children")
    data = c.fetchall()
    conn.close()
    return data

def delete_child(id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM children WHERE id=?", (id,))
    conn.commit()
    conn.close()

# ---------------- FACE MATCH ----------------
def match_face(uploaded_path):
    children = get_children()

    for child in children:
        try:
            result = DeepFace.verify(
                img1_path=uploaded_path,
                img2_path=child[5],
                enforce_detection=False,
                model_name="Facenet"   # best balance for free tier
            )

            if result["verified"]:
                return child
        except:
            continue

    return None

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- UI ----------------
st.title("🔍 Missing Child Detection System")

# -------- NOT LOGGED IN --------
if not st.session_state.user:

    menu = ["Login", "Signup"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Signup":
        st.subheader("Create Account")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Signup"):
            if email and password:
                signup(email, password)
                st.success("✅ Account created! Now login.")
            else:
                st.warning("Enter all fields")

    if choice == "Login":
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            role = login(email, password)

            if role:
                st.session_state.user = role
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

# -------- AFTER LOGIN --------
else:
    role = st.session_state.user

    st.sidebar.success(f"Logged in as {role}")

    menu = ["Upload Child", "Crosscheck", "Dashboard", "Logout"]
    choice = st.sidebar.selectbox("Menu", menu)

    # -------- LOGOUT --------
    if choice == "Logout":
        st.session_state.user = None
        st.rerun()

    # -------- UPLOAD --------
    elif choice == "Upload Child":
        st.subheader("📤 Upload Child")

        name = st.text_input("Name")
        age = st.number_input("Age", 1, 100)
        location = st.text_input("Location")
        contact = st.text_input("Contact Info")
        image = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

        if st.button("Upload"):
            if name and location and contact and image:
                save_child(name, age, location, contact, image)
                st.success("✅ Child uploaded successfully!")
            else:
                st.warning("Fill all fields")

    # -------- CROSSCHECK --------
    elif choice == "Crosscheck":
        st.subheader("🔍 Crosscheck Face")

        image = st.file_uploader("Upload Image to Check", type=["jpg", "png", "jpeg"])

        if st.button("Check"):
            if image:
                temp_path = os.path.join(UPLOAD, "temp.jpg")

                with open(temp_path, "wb") as f:
                    f.write(image.getbuffer())

                st.info("⏳ Checking... please wait")

                match = match_face(temp_path)

                if match:
                    st.success("🎯 MATCH FOUND!")
                    st.write(f"Name: {match[1]}")
                    st.write(f"Age: {match[2]}")
                    st.write(f"Location: {match[3]}")
                    st.write(f"Contact: {match[4]}")
                else:
                    st.error("❌ NOT FOUND")

            else:
                st.warning("Upload an image first")

    # -------- DASHBOARD --------
    elif choice == "Dashboard":
        st.subheader("📊 Children Database")

        children = get_children()

        if not children:
            st.info("No records found")

        for child in children:
            st.write(f"ID: {child[0]}")
            st.write(f"Name: {child[1]}")
            st.write(f"Age: {child[2]}")
            st.write(f"Location: {child[3]}")
            st.write(f"Contact: {child[4]}")

            if role == "admin":
                if st.button(f"Delete ID {child[0]}"):
                    delete_child(child[0])
                    st.warning("🗑️ Deleted!")
                    st.rerun()

            st.markdown("---")
