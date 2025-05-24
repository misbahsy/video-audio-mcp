import os
import sys
import pytest
import shutil
import ffmpeg
import subprocess
import math

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the mcp server functions from server.py
from server import (
    health_check,
    extract_audio_from_video,
    trim_video,
    convert_audio_properties,
    convert_video_properties,
    change_aspect_ratio,
    convert_audio_format,
    set_audio_bitrate,
    set_audio_sample_rate,
    set_audio_channels,
    convert_video_format,
    set_video_resolution,
    set_video_codec,
    set_video_bitrate,
    set_video_frame_rate,
    set_video_audio_track_codec,
    set_video_audio_track_bitrate,
    set_video_audio_track_sample_rate,
    set_video_audio_track_channels,
    add_subtitles,
    add_text_overlay,
    add_image_overlay,
    concatenate_videos,
    change_video_speed,
    remove_silence,
    add_b_roll,
    add_basic_transitions,
    _parse_time_to_seconds
)

# Path to the sample video file
SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "sample.mp4")
SAMPLE_VIDEO_2 = os.path.join(os.path.dirname(__file__), "sample2.mp4")
SAMPLE_IMAGE = os.path.join(os.path.dirname(__file__), "sample.png")

# Create an output directory for test results
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_outputs")
# Directory for sample files used by B-roll and transitions tests
SAMPLE_FILES_DIR = os.path.join(os.path.dirname(__file__), "sample_files")

# --- Helper Functions for B-roll and Transitions Tests ---

def _run_ffmpeg_command(command_args):
    try:
        subprocess.run(["ffmpeg"] + command_args, check=True, capture_output=True)
        print(f"FFmpeg command successful: {' '.join(command_args)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg command failed: {' '.join(command_args)}")
        print(f"Error: {e.stderr.decode() if e.stderr else e}")
        return False
    except FileNotFoundError:
        print("Error: ffmpeg command not found. Please ensure FFmpeg is installed and in your PATH.")
        return False

def setup_broll_test_environment():
    """Creates sample video files needed for B-roll and transition tests."""
    os.makedirs(SAMPLE_FILES_DIR, exist_ok=True)

    sample_files_config = {
        "main_video.mp4": ["-f", "lavfi", "-i", "color=c=black:s=640x360:r=30:d=10", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"],
        "broll1.mp4":     ["-f", "lavfi", "-i", "color=c=red:s=640x360:r=30:d=3", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"],
        "broll2.mp4":     ["-f", "lavfi", "-i", "color=c=blue:s=640x360:r=30:d=2", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"],
        "short_video1.mp4":["-f", "lavfi", "-i", "color=c=green:s=640x360:r=30:d=5", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"],
        "short_video2.mp4":["-f", "lavfi", "-i", "color=c=yellow:s=640x360:r=30:d=4", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"],
    }

    for filename, ffmpeg_args in sample_files_config.items():
        file_path = os.path.join(SAMPLE_FILES_DIR, filename)
        if not os.path.exists(file_path):
            print(f"Creating sample file: {file_path}...")
            if not _run_ffmpeg_command(["-y"] + ffmpeg_args + [file_path]):
                 print(f"WARNING: Failed to create {file_path}. Tests requiring this file may fail.")
        else:
            print(f"Sample file {file_path} already exists.")

def get_media_duration(file_path):
    """Gets media duration using ffprobe."""
    if not os.path.exists(file_path):
        print(f"File not found for duration check: {file_path}")
        return 0
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        # When text=True, e.stderr is already a string
        error_output = e.stderr if e.stderr else str(e)
        print(f"Error probing file {file_path}: {error_output}")
        return 0
    except FileNotFoundError:
        print("Error: ffprobe command not found. Please ensure FFmpeg (and ffprobe) is installed and in your PATH.")
        return 0

def setup_module(module):
    """Setup for the test module - create output directory and sample files"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Test output directory: {OUTPUT_DIR}")
    
    # Setup sample files for B-roll and transitions tests
    setup_broll_test_environment()
    
def teardown_module(module):
    """Teardown for the test module - optionally clean up output directory"""
    # Uncomment the line below if you want to clean up after tests
    # shutil.rmtree(OUTPUT_DIR)
    pass

def test_health_check():
    """Test the health_check function"""
    result = health_check()
    assert result == "Server is healthy!"
    print(f"Health check result: {result}")

def test_extract_audio():
    """Test extracting audio from the sample video"""
    output_path = os.path.join(OUTPUT_DIR, "extracted_audio.mp3")
    result = extract_audio_from_video(SAMPLE_VIDEO, output_path)
    assert "Audio extracted successfully" in result
    assert os.path.exists(output_path)
    print(f"Extracted audio to: {output_path}")
    print(f"Result: {result}")

def test_trim_video():
    """Test trimming the sample video"""
    output_path = os.path.join(OUTPUT_DIR, "trimmed_video.mp4")
    result = trim_video(SAMPLE_VIDEO, output_path, "00:00:00", "00:00:05")
    assert "Video trimmed successfully" in result
    assert os.path.exists(output_path)
    print(f"Trimmed video to: {output_path}")
    print(f"Result: {result}")

def test_convert_audio_properties():
    """Test converting audio properties"""
    # First extract audio to convert
    audio_path = os.path.join(OUTPUT_DIR, "audio_to_convert.mp3")
    extract_audio_from_video(SAMPLE_VIDEO, audio_path)
    
    output_path = os.path.join(OUTPUT_DIR, "converted_audio.wav")
    result = convert_audio_properties(audio_path, output_path, "wav", "192k", 44100, 2)
    assert "Audio converted successfully" in result
    assert os.path.exists(output_path)
    print(f"Converted audio to: {output_path}")
    print(f"Result: {result}")

def test_convert_video_properties():
    """Test converting video properties"""
    output_path = os.path.join(OUTPUT_DIR, "converted_video.mp4")
    result = convert_video_properties(
        SAMPLE_VIDEO, output_path, "mp4", "720", "libx264", 
        "1M", 30, "aac", "128k", 44100, 2
    )
    assert "Video converted successfully" in result
    assert os.path.exists(output_path)
    print(f"Converted video to: {output_path}")
    print(f"Result: {result}")

def test_change_aspect_ratio():
    """Test changing the aspect ratio of the video"""
    output_path = os.path.join(OUTPUT_DIR, "aspect_ratio_video.mp4")
    result = change_aspect_ratio(SAMPLE_VIDEO, output_path, "4:3", "pad")
    assert "Video aspect ratio changed" in result or "Video aspect ratio already matches" in result
    assert os.path.exists(output_path)
    print(f"Changed aspect ratio to: {output_path}")
    print(f"Result: {result}")

def test_convert_audio_format():
    """Test converting audio format"""
    # First extract audio
    audio_path = os.path.join(OUTPUT_DIR, "audio_format_test.mp3")
    extract_audio_from_video(SAMPLE_VIDEO, audio_path)
    
    output_path = os.path.join(OUTPUT_DIR, "converted_audio_format.wav")
    result = convert_audio_format(audio_path, output_path, "wav")
    assert "Audio format converted" in result
    assert os.path.exists(output_path)
    print(f"Converted audio format to: {output_path}")
    print(f"Result: {result}")

def test_set_audio_bitrate():
    """Test setting audio bitrate"""
    # First extract audio
    audio_path = os.path.join(OUTPUT_DIR, "audio_bitrate_test.mp3")
    extract_audio_from_video(SAMPLE_VIDEO, audio_path)
    
    output_path = os.path.join(OUTPUT_DIR, "audio_new_bitrate.mp3")
    result = set_audio_bitrate(audio_path, output_path, "320k")
    assert "Audio bitrate set" in result
    assert os.path.exists(output_path)
    print(f"Set audio bitrate to: {output_path}")
    print(f"Result: {result}")

def test_set_audio_sample_rate():
    """Test setting audio sample rate"""
    # First extract audio
    audio_path = os.path.join(OUTPUT_DIR, "audio_sample_rate_test.mp3")
    extract_audio_from_video(SAMPLE_VIDEO, audio_path)
    
    output_path = os.path.join(OUTPUT_DIR, "audio_new_sample_rate.mp3")
    result = set_audio_sample_rate(audio_path, output_path, 48000)
    assert "Audio sample rate set" in result
    assert os.path.exists(output_path)
    print(f"Set audio sample rate to: {output_path}")
    print(f"Result: {result}")

def test_set_audio_channels():
    """Test setting audio channels"""
    # First extract audio
    audio_path = os.path.join(OUTPUT_DIR, "audio_channels_test.mp3")
    extract_audio_from_video(SAMPLE_VIDEO, audio_path)
    
    output_path = os.path.join(OUTPUT_DIR, "audio_mono.mp3")
    result = set_audio_channels(audio_path, output_path, 1)  # Convert to mono
    assert "Audio channels set" in result
    assert os.path.exists(output_path)
    print(f"Set audio to mono: {output_path}")
    print(f"Result: {result}")

def test_convert_video_format():
    """Test converting video format"""
    output_path = os.path.join(OUTPUT_DIR, "video_format.avi")
    result = convert_video_format(SAMPLE_VIDEO, output_path, "avi")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Converted video format to: {output_path}")
    print(f"Result: {result}")

def test_set_video_resolution():
    """Test setting video resolution"""
    output_path = os.path.join(OUTPUT_DIR, "video_resolution.mp4")
    result = set_video_resolution(SAMPLE_VIDEO, output_path, "640x480")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video resolution to: {output_path}")
    print(f"Result: {result}")

def test_set_video_codec():
    """Test setting video codec"""
    output_path = os.path.join(OUTPUT_DIR, "video_codec.mp4")
    result = set_video_codec(SAMPLE_VIDEO, output_path, "libx264")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video codec to: {output_path}")
    print(f"Result: {result}")

def test_set_video_bitrate():
    """Test setting video bitrate"""
    output_path = os.path.join(OUTPUT_DIR, "video_bitrate.mp4")
    result = set_video_bitrate(SAMPLE_VIDEO, output_path, "2M")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video bitrate to: {output_path}")
    print(f"Result: {result}")

def test_set_video_frame_rate():
    """Test setting video frame rate"""
    output_path = os.path.join(OUTPUT_DIR, "video_frame_rate.mp4")
    result = set_video_frame_rate(SAMPLE_VIDEO, output_path, 24)
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video frame rate to: {output_path}")
    print(f"Result: {result}")

def test_set_video_audio_track_codec():
    """Test setting video audio track codec"""
    output_path = os.path.join(OUTPUT_DIR, "video_audio_codec.mp4")
    result = set_video_audio_track_codec(SAMPLE_VIDEO, output_path, "aac")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video audio codec to: {output_path}")
    print(f"Result: {result}")

def test_set_video_audio_track_bitrate():
    """Test setting video audio track bitrate"""
    output_path = os.path.join(OUTPUT_DIR, "video_audio_bitrate.mp4")
    result = set_video_audio_track_bitrate(SAMPLE_VIDEO, output_path, "192k")
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video audio bitrate to: {output_path}")
    print(f"Result: {result}")

def test_set_video_audio_track_sample_rate():
    """Test setting video audio track sample rate"""
    output_path = os.path.join(OUTPUT_DIR, "video_audio_sample_rate.mp4")
    result = set_video_audio_track_sample_rate(SAMPLE_VIDEO, output_path, 48000)
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video audio sample rate to: {output_path}")
    print(f"Result: {result}")

def test_set_video_audio_track_channels():
    """Test setting video audio track channels"""
    output_path = os.path.join(OUTPUT_DIR, "video_audio_channels.mp4")
    result = set_video_audio_track_channels(SAMPLE_VIDEO, output_path, 1)  # Convert to mono
    assert "Operation successful" in result
    assert os.path.exists(output_path)
    print(f"Set video audio to mono: {output_path}")
    print(f"Result: {result}")

def test_add_text_overlay():
    """Test adding text overlay to video"""
    output_path = os.path.join(OUTPUT_DIR, "video_with_text.mp4")
    text_elements = [
        {
            'text': 'Test Overlay',
            'start_time': 0,
            'end_time': 5,
            'font_size': 30,
            'font_color': 'white',
            'x_pos': 10,
            'y_pos': 10
        }
    ]
    result = add_text_overlay(SAMPLE_VIDEO, output_path, text_elements)
    print(f"Text overlay result: {result}")  # Print full result for debugging
    
    # More flexible assertion that checks for any indication of success
    success_indicators = [
        "Text overlays added successfully",
        "successfully",
        "Operation successful"
    ]
    assert any(indicator in result for indicator in success_indicators), \
        f"Expected success message, got: {result}"
    assert os.path.exists(output_path), \
        f"Expected output file {output_path} to exist"
    print(f"Added text overlay to: {output_path}")

    # Try a more complex overlay with box
    output_path_2 = os.path.join(OUTPUT_DIR, "video_with_text_box.mp4")
    text_elements_2 = [
        {
            'text': 'Test Overlay with Box',
            'start_time': 0,
            'end_time': 5,
            'font_size': 30,
            'font_color': 'white',
            'x_pos': 10,
            'y_pos': 10,
            'box': True,
            'box_color': 'black@0.5'
        }
    ]
    result_2 = add_text_overlay(SAMPLE_VIDEO, output_path_2, text_elements_2)
    print(f"Text overlay with box result: {result_2}")
    assert any(indicator in result_2 for indicator in success_indicators), \
        f"Expected success message for boxed overlay, got: {result_2}"
    assert os.path.exists(output_path_2), \
        f"Expected output file {output_path_2} to exist"
    print(f"Added text overlay with box to: {output_path_2}")

def test_add_subtitles():
    """Test adding subtitles to video"""
    # First create a simple SRT file
    srt_path = os.path.join(OUTPUT_DIR, "test_subtitles.srt")
    with open(srt_path, 'w') as f:
        f.write("1\n00:00:00,000 --> 00:00:05,000\nThis is a test subtitle\n\n")
        f.write("2\n00:00:05,000 --> 00:00:10,000\nSecond subtitle line\n\n")
    
    output_path = os.path.join(OUTPUT_DIR, "video_with_subtitles.mp4")
    font_style = {
        'font_size': 24,
        'font_color': 'white',
        'outline_color': 'black',
        'outline_width': 2
    }
    result = add_subtitles(SAMPLE_VIDEO, srt_path, output_path, font_style)
    print(f"Result: {result}")  # Print the actual result for debugging
    # Check for various possible success messages that might be returned
    assert any(success_msg in result for success_msg in 
               ["Subtitles added successfully", "successfully", "Operation successful"])
    assert os.path.exists(output_path)
    print(f"Added subtitles to: {output_path}")

def test_add_image_overlay():
    """Test adding an image overlay to video"""
    # Use the existing sample.png file
    output_path = os.path.join(OUTPUT_DIR, "video_with_image.mp4")
    
    result = add_image_overlay(
        SAMPLE_VIDEO, output_path, SAMPLE_IMAGE, 
        position='top_right', opacity=0.5, 
        start_time='0', end_time='5', width='iw/2', height='ih/2'
    )
    
    print(f"Result: {result}")  # Print the actual result for debugging
    # Check for various possible success messages
    assert any(success_msg in result for success_msg in 
               ["Image overlay added successfully", "successfully", "Operation successful"])
    assert os.path.exists(output_path)
    print(f"Added image overlay to: {output_path}")

# --- Tests for Phase 4 Functions ---
def test_concatenate_videos():
    """Test concatenating two videos"""
    # First, create two trimmed versions of the same video to ensure compatibility
    trim1_path = os.path.join(OUTPUT_DIR, "trim1.mp4")
    trim2_path = os.path.join(OUTPUT_DIR, "trim2.mp4")
    
    # Create two short clips from the same video
    trim_video(SAMPLE_VIDEO, trim1_path, "00:00:00", "00:00:05")
    trim_video(SAMPLE_VIDEO, trim2_path, "00:00:50", "00:00:55")
    
    # Now concatenate these identical-format videos
    output_path = os.path.join(OUTPUT_DIR, "concatenated_video.mp4")
    video_list = [trim1_path, trim2_path]
    result = concatenate_videos(video_list, output_path)
    
    print(f"Concatenate videos result: {result}")
    assert any(success_msg in result for success_msg in 
               ["Videos concatenated successfully", "successfully", "Operation successful"])
    assert os.path.exists(output_path)
    print(f"Concatenated videos to: {output_path}")

def test_change_video_speed():
    """Test changing video speed with various factors"""
    # Create a short clip for testing speed changes
    short_clip_path = os.path.join(OUTPUT_DIR, "short_clip.mp4")
    result = trim_video(SAMPLE_VIDEO, short_clip_path, "00:00:00", "00:00:30")
    if not os.path.exists(short_clip_path):
        pytest.skip(f"Could not create test clip: {result}")
    
    # Test speeding up (1.5x)
    output_path_fast = os.path.join(OUTPUT_DIR, "video_fast.mp4")
    result_fast = change_video_speed(short_clip_path, output_path_fast, 1.5)
    print(f"Change video speed (1.5x) result: {result_fast}")
    
    # Success checking - accept any indication that the operation completed
    success_indicators = [
        "Video speed changed", 
        "successfully",
        "saved to"
    ]
    assert any(indicator in result_fast for indicator in success_indicators), \
        f"Failed to change video speed. Result: {result_fast}"
    assert os.path.exists(output_path_fast), \
        f"Output file {output_path_fast} was not created"

# Needs more testing
def test_remove_silence():
    """Test removing silence from a video"""
    # Create a short clip for testing silence removal
    short_clip_path = os.path.join(OUTPUT_DIR, "short_clip_for_silence.mp4")
    trim_video(SAMPLE_VIDEO, short_clip_path, "00:00:00", "00:00:50")
    
    output_path = os.path.join(OUTPUT_DIR, "video_no_silence.mp4")
    result = remove_silence(short_clip_path, output_path, silence_threshold_db=-30.0, min_silence_duration_ms=1000)
    
    print(f"Remove silence result: {result}")
    # More flexible assertion - might not find silence in all videos
    assert any(success_msg in result for success_msg in 
               ["Silent segments removed", "No significant silences detected", "successfully"])
    assert os.path.exists(output_path)
    print(f"Removed silence (or copied) to: {output_path}")

def test_trim_video_with_duration_check():
    """Test that verifies video trimming with exact duration checks."""
    # Create output paths for trimmed segments
    trim1_path = os.path.join(OUTPUT_DIR, "trim_duration_check_1.mp4")
    trim2_path = os.path.join(OUTPUT_DIR, "trim_duration_check_2.mp4")
    
    # Trim the videos
    trim_video(SAMPLE_VIDEO, trim1_path, "00:00:00", "00:00:05")
    trim_video(SAMPLE_VIDEO, trim2_path, "00:00:50", "00:00:55")
    
    # Verify durations using ffmpeg probe
    def get_duration(file_path):
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    
    # Check first segment (0-5 seconds)
    duration1 = get_duration(trim1_path)
    assert abs(duration1 - 5.0) < 0.1, f"First segment should be ~5 seconds, got {duration1} seconds"
    
    # Check second segment (50-55 seconds)
    duration2 = get_duration(trim2_path)
    assert abs(duration2 - 5.0) < 0.1, f"Second segment should be ~5 seconds, got {duration2} seconds"
    
    # Clean up
    os.remove(trim1_path)
    os.remove(trim2_path)

# --- Tests for B-roll and Transitions Features ---

def test_add_b_roll():
    """Test adding B-roll overlays to a main video"""
    print("\n--- Testing add_b_roll ---")
    main_video = os.path.join(SAMPLE_FILES_DIR, "main_video.mp4") # 10s
    broll1 = os.path.join(SAMPLE_FILES_DIR, "broll1.mp4") # 3s
    broll2 = os.path.join(SAMPLE_FILES_DIR, "broll2.mp4") # 2s

    if not all(os.path.exists(p) for p in [main_video, broll1, broll2]):
        pytest.skip("Skipping test_add_b_roll: Essential sample files are missing.")

    main_duration = get_media_duration(main_video)
    broll1_duration = get_media_duration(broll1)
    broll2_duration = get_media_duration(broll2)

    # Test 1: Fullscreen B-roll overlay
    output_path1 = os.path.join(OUTPUT_DIR, "broll_test1_fullscreen.mp4")
    broll_clips1 = [
        {
            'clip_path': broll1,
            'insert_at_timestamp': '00:00:02',
            'position': 'fullscreen',
            'transition_in': 'fade',
            'transition_out': 'fade',
            'transition_duration': 0.5
        }
    ]
    result1 = add_b_roll(main_video_path=main_video, broll_clips=broll_clips1, output_video_path=output_path1)
    print(f"Test 1 (fullscreen overlay) result: {result1}")
    if "success" in result1.lower() and os.path.exists(output_path1):
        # Duration should be same as main video
        assert math.isclose(get_media_duration(output_path1), main_duration, rel_tol=0.1), "Test 1 FAILED: Duration mismatch"
        print("  Test 1: PASSED")
    else:
        print("  Test 1: FAILED")
        assert False, "Test 1 Failed"

    # Test 2: Picture-in-Picture B-roll
    output_path2 = os.path.join(OUTPUT_DIR, "broll_test2_pip.mp4")
    broll_clips2 = [
        {
            'clip_path': broll1,
            'insert_at_timestamp': '00:00:03',
            'position': 'top-right',
            'scale': 0.3,
            'transition_in': 'slide_left',
            'transition_out': 'slide_right',
            'transition_duration': 0.7,
            'audio_mix': 0.3
        }
    ]
    result2 = add_b_roll(main_video_path=main_video, broll_clips=broll_clips2, output_video_path=output_path2)
    print(f"Test 2 (picture-in-picture) result: {result2}")
    if "success" in result2.lower() and os.path.exists(output_path2):
        assert math.isclose(get_media_duration(output_path2), main_duration, rel_tol=0.1), "Test 2 FAILED: Duration mismatch"
        print("  Test 2: PASSED")
    else:
        print("  Test 2: FAILED")
        assert False, "Test 2 Failed"

    # Test 3: Multiple B-rolls with different positions
    output_path3 = os.path.join(OUTPUT_DIR, "broll_test3_multiple.mp4")
    broll_clips3 = [
        {
            'clip_path': broll1,
            'insert_at_timestamp': '00:00:01',
            'position': 'bottom-left',
            'scale': 0.4,
            'transition_in': 'slide_up',
            'transition_out': 'fade'
        },
        {
            'clip_path': broll2,
            'insert_at_timestamp': '00:00:04',
            'position': 'top-right',
            'scale': 0.4,
            'transition_in': 'slide_down',
            'transition_out': 'slide_up'
        }
    ]
    result3 = add_b_roll(main_video_path=main_video, broll_clips=broll_clips3, output_video_path=output_path3)
    print(f"Test 3 (multiple positions) result: {result3}")
    if "success" in result3.lower() and os.path.exists(output_path3):
        assert math.isclose(get_media_duration(output_path3), main_duration, rel_tol=0.1), "Test 3 FAILED: Duration mismatch"
        print("  Test 3: PASSED")
    else:
        print("  Test 3: FAILED")
        assert False, "Test 3 Failed"

    # Test 4: Invalid position
    output_path4 = os.path.join(OUTPUT_DIR, "broll_test4_invalid_position.mp4")
    broll_clips4 = [
        {
            'clip_path': broll1,
            'insert_at_timestamp': '0',
            'position': 'invalid-position'
        }
    ]
    result4 = add_b_roll(main_video_path=main_video, broll_clips=broll_clips4, output_video_path=output_path4)
    print(f"Test 4 (invalid position) result: {result4}")
    assert "error" in result4.lower() and "invalid position" in result4.lower(), "Test 4 FAILED: Did not error on invalid position"
    print("  Test 4: PASSED")

    # Test 5: Invalid file path
    output_path5 = os.path.join(OUTPUT_DIR, "broll_test5_invalid_path.mp4")
    broll_clips5 = [
        {'clip_path': "non_existent_broll.mp4", 'insert_at_timestamp': '1'}
    ]
    result5 = add_b_roll(main_video_path=main_video, broll_clips=broll_clips5, output_video_path=output_path5)
    print(f"Test 5 (invalid path) result: {result5}")
    assert "error" in result5.lower() and "not found" in result5.lower(), "Test 5 FAILED: Did not error on invalid path"
    print("  Test 5: PASSED")


def test_add_basic_transitions():
    """Test adding basic transitions to videos"""
    print("\n--- Testing add_basic_transitions ---")
    video_in = os.path.join(SAMPLE_FILES_DIR, "main_video.mp4") # 10s

    if not os.path.exists(video_in):
        pytest.skip("Skipping test_add_basic_transitions: Sample file main_video.mp4 is missing.")

    # Test 1: Fade-in
    output_fade_in = os.path.join(OUTPUT_DIR, "transition_fade_in_output.mp4")
    fade_duration = 2.0
    result_in = add_basic_transitions(video_path=video_in, output_video_path=output_fade_in, transition_type="fade_in", duration_seconds=fade_duration)
    print(f"Test 1 (fade_in) result: {result_in}")
    if "success" in result_in.lower() and os.path.exists(output_fade_in):
        # Duration should remain the same
        assert math.isclose(get_media_duration(output_fade_in), get_media_duration(video_in), rel_tol=0.1), "Test 1 FAILED: Duration mismatch for fade_in"
        print("  Test 1: PASSED")
    else:
        print("  Test 1: FAILED")
        assert False, "Test 1 Failed"

    # Test 2: Fade-out
    output_fade_out = os.path.join(OUTPUT_DIR, "transition_fade_out_output.mp4")
    result_out = add_basic_transitions(video_path=video_in, output_video_path=output_fade_out, transition_type="fade_out", duration_seconds=fade_duration)
    print(f"Test 2 (fade_out) result: {result_out}")
    if "success" in result_out.lower() and os.path.exists(output_fade_out):
        assert math.isclose(get_media_duration(output_fade_out), get_media_duration(video_in), rel_tol=0.1), "Test 2 FAILED: Duration mismatch for fade_out"
        print("  Test 2: PASSED")
    else:
        print("  Test 2: FAILED")
        assert False, "Test 2 Failed"

    # Test 3: Transition duration longer than video
    long_fade_duration = get_media_duration(video_in) + 5.0
    output_fade_long = os.path.join(OUTPUT_DIR, "transition_fade_long_output.mp4")
    result_long = add_basic_transitions(video_path=video_in, output_video_path=output_fade_long, transition_type="fade_in", duration_seconds=long_fade_duration)
    print(f"Test 3 (long fade) result: {result_long}")
    assert "error" in result_long.lower() and "exceed" in result_long.lower(), "Test 3 FAILED: Did not error on overly long transition"
    print("  Test 3: PASSED")

    # Test 4: Invalid transition type
    output_fade_invalid = os.path.join(OUTPUT_DIR, "transition_fade_invalid_output.mp4")
    result_invalid = add_basic_transitions(video_path=video_in, output_video_path=output_fade_invalid, transition_type="slide_left", duration_seconds=fade_duration)
    print(f"Test 4 (invalid type) result: {result_invalid}")
    assert "error" in result_invalid.lower() and "unsupported transition_type" in result_invalid.lower(), "Test 4 FAILED: Did not error on invalid transition type"
    print("  Test 4: PASSED")

def test_concatenate_videos_with_xfade():
    """Test concatenating videos with xfade transitions"""
    print("\n--- Testing concatenate_videos with XFADE ---")
    video1 = os.path.join(SAMPLE_FILES_DIR, "short_video1.mp4") # 5s green
    video2 = os.path.join(SAMPLE_FILES_DIR, "short_video2.mp4") # 4s yellow

    if not (os.path.exists(video1) and os.path.exists(video2)):
        pytest.skip("Skipping test_concatenate_videos_with_xfade: Sample files short_video1.mp4 or short_video2.mp4 are missing.")

    # Test 1: Dissolve transition
    output_path1 = os.path.join(OUTPUT_DIR, "concat_xfade_dissolve.mp4")
    transition_duration = 1.0
    result1 = concatenate_videos(
        video_paths=[video1, video2],
        output_video_path=output_path1,
        transition_effect="dissolve",
        transition_duration=transition_duration
    )
    print(f"Test 1 (dissolve) result: {result1}")
    if "success" in result1.lower() and os.path.exists(output_path1):
        expected_duration = get_media_duration(video1) + get_media_duration(video2) - transition_duration
        actual_duration = get_media_duration(output_path1)
        print(f"  Expected duration: {expected_duration:.2f}s, Actual: {actual_duration:.2f}s")
        assert math.isclose(actual_duration, expected_duration, rel_tol=0.15), "Test 1 FAILED: Duration mismatch"
        print("  Test 1: PASSED")
    else:
        print("  Test 1: FAILED")
        assert False, "Test 1 Failed"

    # Test 2: Wipe transition
    output_path2 = os.path.join(OUTPUT_DIR, "concat_xfade_wipeleft.mp4")
    result2 = concatenate_videos(
        video_paths=[video1, video2],
        output_video_path=output_path2,
        transition_effect="wipeleft",
        transition_duration=transition_duration
    )
    print(f"Test 2 (wipeleft) result: {result2}")
    if "success" in result2.lower() and os.path.exists(output_path2):
        expected_duration = get_media_duration(video1) + get_media_duration(video2) - transition_duration
        actual_duration = get_media_duration(output_path2)
        print(f"  Expected duration: {expected_duration:.2f}s, Actual: {actual_duration:.2f}s")
        assert math.isclose(actual_duration, expected_duration, rel_tol=0.15), "Test 2 FAILED: Duration mismatch"
        print("  Test 2: PASSED")
    else:
        print("  Test 2: FAILED")
        assert False, "Test 2 Failed"

    # Test 3: Invalid transition type
    output_path3 = os.path.join(OUTPUT_DIR, "concat_xfade_invalid.mp4")
    result3 = concatenate_videos(
        video_paths=[video1, video2],
        output_video_path=output_path3,
        transition_effect="invalid_transition",
        transition_duration=transition_duration
    )
    print(f"Test 3 (invalid transition) result: {result3}")
    assert "error" in result3.lower() and "invalid" in result3.lower(), "Test 3 FAILED: Did not error on invalid transition"
    print("  Test 3: PASSED")

    # Test 4: More than two videos with transition (should error)
    output_path4 = os.path.join(OUTPUT_DIR, "concat_xfade_too_many.mp4")
    result4 = concatenate_videos(
        video_paths=[video1, video2, video1],
        output_video_path=output_path4,
        transition_effect="dissolve",
        transition_duration=transition_duration
    )
    print(f"Test 4 (too many videos) result: {result4}")
    assert "error" in result4.lower() and "exactly two videos" in result4.lower(), "Test 4 FAILED: Did not error with too many videos"
    print("  Test 4: PASSED")

if __name__ == "__main__":
    print("Running video function tests...")
    test_health_check()
    test_extract_audio()
    test_trim_video()
    test_convert_audio_properties()
    test_convert_video_properties()
    test_change_aspect_ratio()
    test_convert_audio_format()
    test_set_audio_bitrate()
    test_set_audio_sample_rate()
    test_set_audio_channels()
    test_convert_video_format()
    test_set_video_resolution()
    test_set_video_codec()
    test_set_video_bitrate()
    test_set_video_frame_rate()
    test_set_video_audio_track_codec()
    test_set_video_audio_track_bitrate()
    test_set_video_audio_track_sample_rate()
    test_set_video_audio_track_channels()
    test_add_text_overlay()
    test_add_subtitles()
    test_add_image_overlay()
    test_concatenate_videos()
    test_change_video_speed()
    test_remove_silence()
    test_trim_video_with_duration_check()
    # New tests for B-roll and transitions
    test_add_b_roll()
    test_add_basic_transitions()
    test_concatenate_videos_with_xfade()
    print("All tests completed!") 