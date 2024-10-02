# helpers.py
import streamlit as st
from streamlit_extras.switch_page_button import switch_page

def add_back_and_logout_button():
    """
    Adds a Back button at the top left of the page.
    Navigates to the previous page in the history stack.
    """
    col1, col2 = st.columns([1, 0.2])
    with col1:
        if len(st.session_state['page_history']) > 1:
        # Create two columns: one for the back button, and one empty
        
        
            if st.button("Back"):
                # Remove the current page from history
                st.session_state['page_history'].pop()
                # Get the previous page
                previous_page = st.session_state['page_history'][-1]
                # Navigate to the previous page
                switch_page(previous_page)

    
    with col2:
        if st.button("Logout"):
            st.session_state["logged_in"] = False
            switch_page("login")
