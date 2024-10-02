import os
import numpy as np
from moviepy.editor import *
from moviepy.video.tools.segmenting import findObjects
from moviepy.config import change_settings

# Set ImageMagick binary path
change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

def split_text(content, max_chars=25):
    # Split the content into two lines if it's too long
    if len(content) > max_chars:
        first_line = content[:max_chars].rsplit(' ', 1)[0]  # Split by space to avoid cutting words
        second_line = content[len(first_line):].strip()
        return [first_line, second_line]
    return [content]

def generating_effects(content):
    # screen size
    screensize = (1920, 1080)
    
    # Split the content into two lines if it's too long
    lines = split_text(content)

    # Create individual text clips for each line
    txtClips = []
    for i, line in enumerate(lines):
        txtClip = TextClip(line, color='white', font="Amiri-Bold", kerning=5, fontsize=80)
        position = ('center', screensize[1] * (0.4 + i * 0.15))  # Slightly offset the second line
        txtClips.append(txtClip.set_pos(position))

    # Create a composite video of given size
    cvc = CompositeVideoClip(txtClips, size=screensize)

    # Helper function for rotation matrix
    rotMatrix = lambda a: np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])

    def effect1(screenpos, i, nletters):
        d = lambda t: 1.0 / (0.3 + t**8)  # Damping
        a = i * np.pi / nletters  # Angle of the movement
        v = rotMatrix(a).dot([-1, 0])
        if i % 2:
            v[1] = -v[1]
        return lambda t: screenpos + 400 * d(t) * rotMatrix(0.5 * d(t) * a).dot(v)

    # A list of ImageClips (letters)
    letters = findObjects(cvc, 50)

    # Method to move letters
    def moveLetters(letters, funcpos):
        return [letter.set_pos(funcpos(letter.screenpos, i, len(letters)))
                for i, letter in enumerate(letters)]

    # Adding clips with the specific effect
    clips = [CompositeVideoClip(moveLetters(letters, funcpos),
                                size=screensize).subclip(0, 5)
             for funcpos in [effect1]]

    # Composing all the clips
    final_clip = concatenate_videoclips(clips)

    # Setting fps of the final clip
    final_clip.fps = 24

    # Define the path to save the video in "videos" directory
    video_path = os.path.join("videos", "final_clip.mp4")

    # Save the final clip to the specified path in mp4 format
    final_clip.write_videofile(video_path, codec="libx264")

    # Return the video path
    return video_path
