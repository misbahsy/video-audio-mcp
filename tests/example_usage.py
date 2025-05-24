#!/usr/bin/env python3
"""
Example usage of the video editing MCP tools.
This file demonstrates how to use the MCP tools directly in your Python code.
"""

import os
import sys

# Add the parent directory to sys.path to import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from server.py
from server import (
    extract_audio_from_video,
    trim_video,
    add_text_overlay
)

def main():
    # Define paths
    sample_video = os.path.join(os.path.dirname(__file__), "sample.mp4")
    output_dir = os.path.join(os.path.dirname(__file__), "example_outputs")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Using sample video: {sample_video}")
    print(f"Output directory: {output_dir}")
    
    # Example 1: Extract audio from video
    audio_output = os.path.join(output_dir, "extracted_audio.mp3")
    print("\n1. Extracting audio from video:")
    result = extract_audio_from_video(sample_video, audio_output)
    print(f"Result: {result}")
    
    # Example 2: Trim the first 5 seconds of the video
    trimmed_output = os.path.join(output_dir, "trimmed_5sec.mp4")
    print("\n2. Trimming video to first 5 seconds:")
    result = trim_video(sample_video, trimmed_output, "00:00:00", "00:00:05")
    print(f"Result: {result}")
    
    # Example 3: Add text overlay to the video
    text_overlay_output = os.path.join(output_dir, "with_text_overlay.mp4")
    text_elements = [
        {
            'text': 'Sample Video',
            'start_time': 0,
            'end_time': 3,
            'font_size': 40,
            'font_color': 'white',
            'x_pos': '10',  # Fixed position from left
            'y_pos': '10',  # Fixed position from top
            'box': True,
            'box_color': 'black@0.5'
        },
        {
            'text': 'Created with MCP Tools',
            'start_time': 3,
            'end_time': 6,
            'font_size': 30,
            'font_color': 'yellow',
            'x_pos': '10',  # Fixed position from left
            'y_pos': 'h-50',  # 50 pixels from bottom
            'box': True,
            'box_color': 'blue@0.5'
        }
    ]
    print("\n3. Adding text overlay to video:")
    result = add_text_overlay(sample_video, text_overlay_output, text_elements)
    print(f"Result: {result}")
    
    print("\nAll examples completed!")
    print(f"Check the output files in: {output_dir}")

if __name__ == "__main__":
    main() 