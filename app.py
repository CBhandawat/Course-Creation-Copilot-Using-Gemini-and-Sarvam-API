# app.py
import streamlit as st
from streamlit_extras.switch_page_button import switch_page

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(**st.secrets["mongo"])

client = init_connection()

# Set up the Streamlit page configuration
st.set_page_config(page_title="EduPilot",initial_sidebar_state="collapsed")
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

# Initialize navigation history
if 'page_history' not in st.session_state:
    st.session_state['page_history'] = []

# Display the main page content
st.title("Welcome to EduPilot")
st.image("logo/EduPilot_Logo.png", width=300)

if st.button("Let's Create a Course"):
    switch_page("login")
# Load the content of the current page
# Streamlit will automatically run the appropriate page script from the 'pages' folder
