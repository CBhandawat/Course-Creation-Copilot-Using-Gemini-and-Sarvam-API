import streamlit as st
import os
import requests
import base64
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
import uuid
from io import BytesIO
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import gridfs
import tempfile
from bson import ObjectId
from helpers import add_back_and_logout_button
from effects import generating_effects
from streamlit_extras.switch_page_button import switch_page


# Set up the Streamlit page configuration
st.set_page_config(page_title="Video Generation", initial_sidebar_state="collapsed")
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

# Ensure necessary directories exist
def ensure_directories():
    directories = ["slides", "audio", "videos"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

ensure_directories()

# MongoDB setup
def get_database():
    # Replace the URI string with your MongoDB deployment's connection string.
    client = MongoClient(os.getenv("MONGODB_URI"))  # Update with your MongoDB URI
    return client["course_copilot_db"]

db = get_database()
topics_collection = db["topics"]
fs = gridfs.GridFS(db)


def load_module_data(topic):
    """
    Load module data from MongoDB, including slides and the generated video.
    Retrieves the video from GridFS.
    """
    try:
        module_data = topics_collection.find_one({"user_id": st.session_state['user_id'], "topic_name": topic})
        if module_data:
            slides = module_data.get("slides", [])
            video_id = module_data.get("video_id")
            notes = module_data.get("notes")
            # Retrieve video binary from GridFS
            if video_id:
                video_binary = fs.get(video_id).read()
                
                # Save the video temporarily to display it
                temp_video_path = f"videos/temp_{uuid.uuid4()}.mp4"
                with open(temp_video_path, "wb") as f:
                    f.write(video_binary)
                
                return slides, temp_video_path, notes
            else:
                return slides, None, None
        else:
            return None, None, None
    except PyMongoError as e:
        st.error(f"MongoDB Error while loading topic data: {e}")
        return None, None
    except Exception as e:
        st.error(f"Unexpected error while loading topic data: {e}")
        return None, None


def reset_module_data(selected_topic):
    if st.session_state.get('PREVIOUS_TOPIC') != selected_topic:
        st.session_state['slides'] = [{'content': '', 'image_desc': ''}]
        st.session_state['PREVIOUS_TOPIC'] = selected_topic

def translateText(result, language, api_key):
    url = "https://api.sarvam.ai/translate"

    payload = {
        "input": result,
        "source_language_code": "en-IN",
        "target_language_code": language,
        "speaker_gender": "Female",
        "mode": "formal",
        "model": "mayura:v1",
        "enable_preprocessing": True
    }
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        return response_data.get("translated_text")
    else:
        st.error(f"Sarvam Translate API Error: {response.status_code} - {response.text}")
        return None

# Sarvam API for text-to-speech
def sarvam_text_to_speech(text_chunk, api_key, speaker):
    url = "https://api.sarvam.ai/text-to-speech"
    
    payload = {
        "speaker": speaker,
        "target_language_code": "hi-IN",
        "inputs": [text_chunk],
        "pitch": 1,
        "pace": 1,
        "loudness": 1,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }
    
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        audio_data_base64 = response_data.get("audios")[0]  # Assuming there's always one audio per chunk
        audio_data = base64.b64decode(audio_data_base64)
        audio_path = f"audio/{uuid.uuid4()}.wav"
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        return audio_path
    else:
        st.error(f"Sarvam TTS API Error: {response.status_code} - {response.text}")
        return None

def generate_slide_image(slide_content, vertex_image_path):
    slide_image_path = f"slides/{uuid.uuid4()}.jpg"
    img = Image.new('RGB', (1920, 1080), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)

    # Load a font (ensure you have a .ttf file, or use a default font)
    try:
        font = ImageFont.truetype("arial.ttf", 50)  # Adjust the font size
    except IOError:
        font = ImageFont.load_default()

    # Define text properties
    text_color = (255, 255, 255)  # White text
    text_position = (100, 100)    # Starting position (top left corner)

    # Wrap the text to fit the image width
    max_width = 1800  # Set the max width for text wrapping
    lines = []
    words = slide_content.split(' ')
    line = ""
    
    for word in words:
        test_line = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]

        if test_width <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    
    lines.append(line)

    # Draw text lines
    y_offset = text_position[1]
    for line in lines:
        draw.text((text_position[0], y_offset), line, font=font, fill=text_color)
        y_offset += 60

    # Insert the DALL·E image if available
    if vertex_image_path:
        try:
            vertex_img = Image.open(vertex_image_path)
            # Resize and position the DALL·E image
            vertex_img = vertex_img.resize((400, 400))
            # Center the image horizontally but keep the y position same
            img_width, img_height = img.size
            image_width, image_height = vertex_img.size

            image_x_position = (img_width - image_width) // 2  # Center horizontally
            image_y_position = 600  # Same y position

            img.paste(vertex_img, (image_x_position, image_y_position))  
        except Exception as e:
            st.error(f"Failed to add DALL·E image to slide: {e}")
    
    # Save the slide
    img.save(slide_image_path)
    
    return slide_image_path

def generate_images_vertex_ai(content, api_key):
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel

    # Initialize Vertex AI
    vertexai.init(project="course-creation-copilot")  # Ensure the project ID is correct

    generation_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

    image = generation_model.generate_images(
        prompt=content,
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level="block_some",
        person_generation="allow_adult",
    )

    # Save the generated image
    image_path = f"slides/{uuid.uuid4()}.jpg"
    image[0].save(image_path)  # Save the generated image
    return image_path

# Merge image and audio into a video
def merge_image_audio(image_path, audio_path, output_path):
    try:
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        image_clip = ImageClip(image_path).set_duration(duration).set_audio(audio_clip)
        image_clip.write_videofile(output_path, codec="libx264", fps=24)
        return output_path
    except Exception as e:
        st.error(f"Error merging video: {e}")
        return None

def merge_video_audio(video_path, audio_path, output_path):
    # Load video and audio clips
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # Set video duration to max_duration (extend video if needed)
    final_video = video.set_duration(audio.duration).set_audio(audio)

    # Write the final video with the merged audio
    final_video.write_videofile(output_path, codec="libx264", fps=24)

    return output_path

# Function to create a pause clip (blank video)
def create_pause_clip(duration=0.1, resolution=(1280, 720), color=(73, 109, 137)):
    # Create a blank (black) video for the given duration
    pause_clip = ColorClip(size=resolution, color=color, duration=duration)
    return pause_clip

# Combine individual slide videos with pauses
def combine_videos(video_paths, output_path):
    pause_duration = 0.1
    try:
        video_clips = []
        for idx, video_path in enumerate(video_paths):
            # Load each video
            video_clip = VideoFileClip(video_path)
            video_clips.append(video_clip)
            
            # Add a pause after each video except the last one
            if idx < len(video_paths) - 1:
                pause_clip = create_pause_clip(duration=pause_duration, resolution=video_clip.size)
                video_clips.append(pause_clip)
        
        # Combine the video clips
        final_video = concatenate_videoclips(video_clips, method="compose")
        final_video.write_videofile(output_path, fps=24)
        return output_path
    except Exception as e:
        st.error(f"Error combining videos: {e}")
        return None

# Function to load module data
def load_module_data_on_selection(selected_topic):
    slides, video_path, notes = load_module_data(selected_topic)
    if slides is not None:
        st.session_state['slides'] = [{"content": slide["content"], "image_desc": slide["image_desc"]} for slide in slides]
        if video_path:
            st.session_state['final_video'] = video_path
            st.success(f"Loaded data for topic: {selected_topic}")
    else:
        st.session_state['slides'] = [{'content': '', 'image_desc': ''}]
        st.session_state.pop('final_video', None)

def save_generated_content_to_db(selected_topic, slides, final_video_path, lecture_notes):
    # Save the video to MongoDB GridFS and get the video_id
    try:
        with open(final_video_path, "rb") as f:
            video_binary = f.read()
        video_id = fs.put(video_binary, filename=os.path.basename(final_video_path), topic_name=selected_topic)
    except Exception as e:
        st.error(f"Failed to upload video to MongoDB: {e}")
        return
    
    # Create a list of slide content and image descriptions
    slide_data = [{"content": slide['content'], "image_desc": slide['image_desc']} for slide in slides]
    
    # Save the data in the database
    try:
        module_data = {
            "user_id": st.session_state['user_id'],
            "topic_name": selected_topic,
            "slides": slide_data,
            "video_id": video_id,
            "notes": lecture_notes
        }
        topics_collection.update_one({"topic_name": selected_topic}, {"$set": module_data}, upsert=True)
    except PyMongoError as e:
        st.error(f"MongoDB Error while saving topic data: {e}")
    except Exception as e:
        st.error(f"Unexpected error while saving topic data: {e}")

# Function to validate if any slide has content
def validate_slides_have_content():
    return any(slide['content'].strip() for slide in st.session_state['slides'])

# Script and video generation page
def script_and_video_generation_page():
    selected_module = st.session_state.get('SELECTED_MODULE')
    selected_topic = st.session_state.get('SELECTED_TOPIC')
    
    if not selected_module or not selected_topic:
        st.error("No module or topic selected.")
        return
    
    # Reset module data if module has changed
    reset_module_data(selected_topic)
    
    # Load module data if it exists
    loaded_slides, loaded_video_path, notes = load_module_data(selected_topic)
    if loaded_slides is not None:
        load_module_data_on_selection(selected_topic)
    
    st.title("Script & Video Generation")
    st.header(f"{selected_module} - {selected_topic}")
    
    
    st.header("Content")
    for i, slide in enumerate(st.session_state['slides']):
        # Create two columns for content and image description
        col1, col2 = st.columns(2)
        with col1:
            slide['content'] = st.text_area(
                f"Slide {i+1} Content (max 480 characters)",
                value=slide['content'],
                max_chars=480,
                height=200
            )
        with col2:
            slide['image_desc'] = st.text_area(
                f"Image description for Slide {i+1}",
                value=slide['image_desc'],
                height=200
            )
    
    # Button to add a new slide
    if st.button("Add Slide"):
        st.session_state['slides'].append({'content': '', 'image_desc': ''})

    if loaded_video_path:
        st.subheader("Existing Video from Database:")
        st.video(loaded_video_path)
    
    if notes:
        st.subheader("Existing Notes from Database:")
        for idx, note in enumerate(notes, start=1):
            st.write(f"Slide {idx} Notes: {note}")
    
    if st.button("Generate Video"):
        # Validate that at least one slide has content
        if not validate_slides_have_content():
            st.error("Please provide content for at least one slide.")
            return
        
        # Ensure that each slide with content has an image description
        for idx, slide in enumerate(st.session_state['slides'], 1):
            if slide['content'].strip() and not slide['image_desc'].strip():
                st.error(f"Please provide an image description for Slide {idx}.")
                return
        
        slide_contents = [slide['content'] for slide in st.session_state['slides'] if slide['content'].strip()]
        slide_images = [slide['image_desc'] for slide in st.session_state['slides'] if slide['content'].strip()]
        
        if len(slide_contents) != len(slide_images):
            st.error("Each slide with content must have an image description.")
            return
        
        audio_paths = []
        heading = f"In this video, we will discuss {selected_topic}."
        audio_path = sarvam_text_to_speech(heading, st.session_state('sarvam_api_key'), st.session_state['SPEAKER'])
        audio_paths.append(audio_path)
        
        video_paths = []
        heading_video_path = generating_effects(selected_topic)
        heading_video_with_audio = "videos/heading.mp4"
        merged_heading_video = merge_video_audio(heading_video_path, audio_path, heading_video_with_audio)
        video_paths.append(merged_heading_video)

        slide_paths = []

        with st.spinner("Generating Video Shortly..."):
            for i, (slide_content, slide_image_desc) in enumerate(zip(slide_contents, slide_images), 1):
                # Generate image using Vertex AI
                image = generate_images_vertex_ai(slide_image_desc, st.session_state('google_api_key'))
                slide_image_path = generate_slide_image(slide_content, image)
                slide_paths.append(slide_image_path)

                # Generate audio for the slide
                audio_path = sarvam_text_to_speech(slide_content, st.session_state('sarvam_api_key'), st.session_state['SPEAKER'])
                if not audio_path:
                    st.error(f"Failed to generate audio for Slide {i}")
                    return
                audio_paths.append(audio_path)

                # Merge slide image with audio
                video_path = f"videos/slide_{i}_{uuid.uuid4()}.mp4"
                merged_video_path = merge_image_audio(slide_image_path, audio_path, video_path)
                if not merged_video_path:
                    st.error(f"Failed to generate video for Slide {i}")
                    return
                video_paths.append(merged_video_path)

            # Combine all individual slide videos into a single video
            final_video_path = f"videos/final_{uuid.uuid4()}.mp4"
            combined_video_path = combine_videos(video_paths, final_video_path)

        if combined_video_path:
            st.video(combined_video_path)
        
        
        
        # Translate lecture notes
        lecture_notes = []
        for slide in slide_contents:
            translated_text = translateText(slide, st.session_state['TRANSLATION_LANGUAGE'], st.session_state('sarvam_api_key'))
            if translated_text:
                lecture_notes.append(translated_text)
            else:
                st.error("Failed to translate slide content.")
                return
            
        # Save the generated video and slides to the database
        save_generated_content_to_db(selected_topic, st.session_state['slides'], combined_video_path, lecture_notes)

        # Display Lecture Notes
        st.subheader("Lecture Notes In Your Preferred Language")
        for idx, notes in enumerate(lecture_notes, start=1):
            st.write(f"Slide {idx} Notes: {notes}")

# Manage navigation history
current_page = "script_and_video_generation"

if 'page_history' not in st.session_state:
    st.session_state['page_history'] = []

if current_page not in st.session_state['page_history']:
    st.session_state['page_history'].append(current_page)

# Add the Back button (if necessary)
add_back_and_logout_button()

# Render the script and video generation page
script_and_video_generation_page()
