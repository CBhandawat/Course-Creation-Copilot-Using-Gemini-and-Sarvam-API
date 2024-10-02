import streamlit as st
import os
import bcrypt
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from streamlit_extras.switch_page_button import switch_page
import time

# Initialize MongoDB Client
def get_database():
    client = MongoClient(**st.secrets["mongo"])  
    return client["course_copilot_db"]

db = get_database()
users_collection = db["users"]

# Streamlit Page Configuration
st.set_page_config(page_title="Login", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {
            display: none
        }
    </style>
    """,
    unsafe_allow_html=True,
)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def register_user(username, password):
    try:
        if users_collection.find_one({"username": username}):
            st.warning("Username already exists. Please choose a different one.")
            return False
        hashed_pw = hash_password(password)
        users_collection.insert_one({
            "username": username,
            "hashed_password": hashed_pw,
            "created_at": time.time(),
        })
        st.success("Registration successful! You can now log in.")
        return True
    except PyMongoError as e:
        st.error(f"Database error during registration: {e}")
        return False
    except Exception as e:
        st.error(f"Unexpected error during registration: {e}")
        return False

def login_user(username, password):
    try:
        user = users_collection.find_one({"username": username})
        if user and verify_password(password, user["hashed_password"]):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['user_id'] = str(user["_id"])
            st.success("Logged in successfully!")
            return True
        else:
            st.error("Invalid username or password.")
            return False
    except PyMongoError as e:
        st.error(f"Database error during login: {e}")
        return False
    except Exception as e:
        st.error(f"Unexpected error during login: {e}")
        return False

def login_page():
    st.title("Login")
    menu = ["Login", "Register"]
    choice = st.radio("Choose an option", menu)

    if choice == "Login":
        st.subheader("Login to Your Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        google_api_key = st.text_input("Google API Key")  # New input for Google API key
        sarvam_api_key = st.text_input("Sarvam API Key")  # New input for Sarvam API key

        if st.button("Login"):
            if login_user(username, password):
                st.session_state['google_api_key'] = google_api_key  # Store Google API key in session
                st.session_state['sarvam_api_key'] = sarvam_api_key  # Store Sarvam API key in session
                switch_page("settings")  # Redirect to settings or main page after login

    elif choice == "Register":
        st.subheader("Create a New Account")
        username = st.text_input("Username", key="reg_username")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        google_api_key = st.text_input("Google API Key (optional)", key="reg_google_api_key")  # New input for Google API key
        sarvam_api_key = st.text_input("Sarvam API Key (optional)", key="reg_sarvam_api_key")  # New input for Sarvam API key
        
        if st.button("Register"):
            if password != confirm_password:
                st.warning("Passwords do not match. Please try again.")
            elif len(password) < 6:
                st.warning("Password should be at least 6 characters long.")
            else:
                if register_user(username, password):
                    st.session_state['google_api_key'] = google_api_key  # Store Google API key in session
                    st.session_state['sarvam_api_key'] = sarvam_api_key  # Store Sarvam API key in session
                    st.info("Please proceed to login.")

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = ""
if 'google_api_key' not in st.session_state:
    st.session_state['google_api_key'] = ""  # Initialize Google API key in session
if 'sarvam_api_key' not in st.session_state:
    st.session_state['sarvam_api_key'] = ""  # Initialize Sarvam API key in session

# Manage navigation history
current_page = "login"

if current_page not in st.session_state.get('page_history', []):
    if 'page_history' not in st.session_state:
        st.session_state['page_history'] = []
    st.session_state['page_history'].append(current_page)

# Render the login page if not logged in
if not st.session_state['logged_in']:
    login_page()
else:
    st.success(f"Welcome, {st.session_state['username']}!")
    switch_page("settings")  # Redirect to settings or main page if already logged in
