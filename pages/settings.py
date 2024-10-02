import streamlit as st
from helpers import add_back_and_logout_button
from streamlit_extras.switch_page_button import switch_page

# Set up the Streamlit page configuration
st.set_page_config(page_title="Settings",initial_sidebar_state="collapsed")
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


def settings_page():
    st.title("Settings")

    target_language_options = ['hi-IN', 'bn-IN', 'kn-IN', 'ml-IN', 'mr-IN', 'od-IN', 'pa-IN', 'ta-IN', 'te-IN', 'gu-IN']
    speaker_options = ['meera', 'pavithra', 'maitreyi', 'arvind', 'amol', 'amartya']

    selected_target_language = st.selectbox("Select the Indian Dialect for Voiceover:", target_language_options)
    selected_speaker = st.selectbox("Select the Speaker for Voiceover:", speaker_options)
    selected_translation_language = st.selectbox("Select Language for Translation:", target_language_options)

    if st.button("Save Settings and Move Forward"):
        st.session_state['TARGET_LANGUAGE'] = selected_target_language
        st.session_state['SPEAKER'] = selected_speaker
        st.session_state['TRANSLATION_LANGUAGE'] = selected_translation_language
        st.success("Settings saved successfully!")
        switch_page("course_idea")

# Manage navigation history
current_page = "settings"

if current_page not in st.session_state['page_history']:
    st.session_state['page_history'].append(current_page)

# Add the Back button
add_back_and_logout_button()

settings_page()
