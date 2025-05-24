import ffmpeg
from mcp.server.fastmcp import FastMCP, Context
import os # For checking file existence if needed, though ffmpeg handles it
import re # For parsing silencedetect output
import tempfile # For add_b_roll
import shutil # For cleaning up temporary directories
import subprocess # For running external commands

# Create an MCP server instance
mcp = FastMCP("VideoAudioServer")

# Add a simple health_check tool
@mcp.tool()
def health_check() -> str:
    """Returns a simple health status to confirm the server is running."""
    return "Server is healthy!"

@mcp.tool()
def extract_audio_from_video(video_path: str, output_audio_path: str, audio_codec: str = 'mp3') -> str:
    """Extracts audio from a video file and saves it.
    
    Args:
        video_path: The path to the input video file.
        output_audio_path: The path to save the extracted audio file.
        audio_codec: The audio codec to use for the output (e.g., 'mp3', 'aac', 'wav'). Defaults to 'mp3'.
    Returns:
        A status message indicating success or failure.
    """
    try:
        input_stream = ffmpeg.input(video_path)
        output_stream = input_stream.output(output_audio_path, acodec=audio_codec)
        output_stream.run(capture_stdout=True, capture_stderr=True)
        return f"Audio extracted successfully to {output_audio_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error extracting audio: {error_message}"
    except FileNotFoundError:
        return f"Error: Input video file not found at {video_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def trim_video(video_path: str, output_video_path: str, start_time: str, end_time: str) -> str:
    """Trims a video to the specified start and end times.

    Args:
        video_path: The path to the input video file.
        output_video_path: The path to save the trimmed video file.
        start_time: The start time for trimming (HH:MM:SS or seconds).
        end_time: The end time for trimming (HH:MM:SS or seconds).
    Returns:
        A status message indicating success or failure.
    """
    try:
        input_stream = ffmpeg.input(video_path, ss=start_time, to=end_time)
        # Attempt to copy codecs to avoid re-encoding if possible
        output_stream = input_stream.output(output_video_path, c='copy') 
        output_stream.run(capture_stdout=True, capture_stderr=True)
        return f"Video trimmed successfully (codec copy) to {output_video_path}"
    except ffmpeg.Error as e:
        error_message_copy = e.stderr.decode('utf8') if e.stderr else str(e)
        try:
            # Fallback to re-encoding if codec copy fails
            input_stream_recode = ffmpeg.input(video_path, ss=start_time, to=end_time)
            output_stream_recode = input_stream_recode.output(output_video_path)
            output_stream_recode.run(capture_stdout=True, capture_stderr=True)
            return f"Video trimmed successfully (re-encoded) to {output_video_path}"
        except ffmpeg.Error as e_recode:
            error_message_recode = e_recode.stderr.decode('utf8') if e_recode.stderr else str(e_recode)
            return f"Error trimming video. Copy attempt: {error_message_copy}. Re-encode attempt: {error_message_recode}"
    except FileNotFoundError:
        return f"Error: Input video file not found at {video_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def convert_audio_properties(input_audio_path: str, output_audio_path: str, target_format: str, 
                               bitrate: str = None, sample_rate: int = None, channels: int = None) -> str:
    """Converts audio file format and ALL specified properties like bitrate, sample rate, and channels.

    Args:
        input_audio_path: Path to the source audio file.
        output_audio_path: Path to save the converted audio file.
        target_format: Desired output audio format (e.g., 'mp3', 'wav', 'aac').
        bitrate: Target audio bitrate (e.g., '128k', '192k'). Optional.
        sample_rate: Target audio sample rate in Hz (e.g., 44100, 48000). Optional.
        channels: Number of audio channels (1 for mono, 2 for stereo). Optional.
    Returns:
        A status message indicating success or failure.
    """
    try:
        stream = ffmpeg.input(input_audio_path)
        kwargs = {}
        if bitrate: 
            kwargs['audio_bitrate'] = bitrate
        if sample_rate: 
            kwargs['ar'] = sample_rate
        if channels: 
            kwargs['ac'] = channels
        kwargs['format'] = target_format

        output_stream = stream.output(output_audio_path, **kwargs)
        output_stream.run(capture_stdout=True, capture_stderr=True)
        return f"Audio converted successfully to {output_audio_path} with format {target_format} and specified properties."
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error converting audio properties: {error_message}"
    except FileNotFoundError:
        return f"Error: Input audio file not found at {input_audio_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def convert_video_properties(input_video_path: str, output_video_path: str, target_format: str,
                               resolution: str = None, video_codec: str = None, video_bitrate: str = None,
                               frame_rate: int = None, audio_codec: str = None, audio_bitrate: str = None,
                               audio_sample_rate: int = None, audio_channels: int = None) -> str:
    """Converts video file format and ALL specified properties like resolution, codecs, bitrates, and frame rate.
    Args listed in PRD.
    Returns:
        A status message indicating success or failure.
    """
    try:
        stream = ffmpeg.input(input_video_path)
        kwargs = {}
        vf_filters = []

        if resolution and resolution.lower() != 'preserve':
            if 'x' in resolution: 
                vf_filters.append(f"scale={resolution}")
            else: 
                vf_filters.append(f"scale=-2:{resolution}")
        
        if vf_filters:
            kwargs['vf'] = ",".join(vf_filters)

        if video_codec: kwargs['vcodec'] = video_codec
        if video_bitrate: kwargs['video_bitrate'] = video_bitrate
        if frame_rate: kwargs['r'] = frame_rate
        if audio_codec: kwargs['acodec'] = audio_codec
        if audio_bitrate: kwargs['audio_bitrate'] = audio_bitrate
        if audio_sample_rate: kwargs['ar'] = audio_sample_rate
        if audio_channels: kwargs['ac'] = audio_channels
        kwargs['format'] = target_format

        output_stream = stream.output(output_video_path, **kwargs)
        output_stream.run(capture_stdout=True, capture_stderr=True)
        return f"Video converted successfully to {output_video_path} with format {target_format} and specified properties."
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error converting video properties: {error_message}"
    except FileNotFoundError:
        return f"Error: Input video file not found at {input_video_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def change_aspect_ratio(video_path: str, output_video_path: str, target_aspect_ratio: str, 
                          resize_mode: str = 'pad', padding_color: str = 'black') -> str:
    """Changes the aspect ratio of a video, using padding or cropping.
    Args listed in PRD.
    Returns:
        A status message indicating success or failure.
    """
    try:
        probe = ffmpeg.probe(video_path)
        video_stream_info = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream_info:
            return "Error: No video stream found in the input file."

        original_width = int(video_stream_info['width'])
        original_height = int(video_stream_info['height'])

        num, den = map(int, target_aspect_ratio.split(':'))
        target_ar_val = num / den
        original_ar_val = original_width / original_height

        vf_filter = ""
        # Attempt to copy codecs if the operation doesn't strictly require re-encoding video stream
        # This is mostly for padding. Cropping implies re-encoding the video stream.
        codec_to_use = None 

        if resize_mode == 'pad':
            if abs(original_ar_val - target_ar_val) < 1e-4:
                try:
                    ffmpeg.input(video_path).output(output_video_path, c='copy').run(capture_stdout=True, capture_stderr=True)
                    return f"Video aspect ratio already matches. Copied to {output_video_path}."
                except ffmpeg.Error:
                     # If copy fails, just re-encode
                    ffmpeg.input(video_path).output(output_video_path).run(capture_stdout=True, capture_stderr=True)
                    return f"Video aspect ratio already matches. Re-encoded to {output_video_path}."
            
            if original_ar_val > target_ar_val: 
                final_w = int(original_height * target_ar_val)
                final_h = original_height
                vf_filter = f"scale={final_w}:{final_h}:force_original_aspect_ratio=decrease,pad={final_w}:{final_h}:(ow-iw)/2:(oh-ih)/2:{padding_color}"
            else: 
                final_w = original_width
                final_h = int(original_width / target_ar_val)
                vf_filter = f"scale={final_w}:{final_h}:force_original_aspect_ratio=decrease,pad={final_w}:{final_h}:(ow-iw)/2:(oh-ih)/2:{padding_color}"
            codec_to_use = 'copy' # Try to copy for padding, audio will be copied too

        elif resize_mode == 'crop':
            if abs(original_ar_val - target_ar_val) < 1e-4:
                try:
                    ffmpeg.input(video_path).output(output_video_path, c='copy').run(capture_stdout=True, capture_stderr=True)
                    return f"Video aspect ratio already matches. Copied to {output_video_path}."
                except ffmpeg.Error:
                    ffmpeg.input(video_path).output(output_video_path).run(capture_stdout=True, capture_stderr=True)
                    return f"Video aspect ratio already matches. Re-encoded to {output_video_path}."
            
            if original_ar_val > target_ar_val: 
                new_width = int(original_height * target_ar_val)
                vf_filter = f"crop={new_width}:{original_height}:(iw-{new_width})/2:0"
            else: 
                new_height = int(original_width / target_ar_val)
                vf_filter = f"crop={original_width}:{new_height}:0:(ih-{new_height})/2"
        else:
            return f"Error: Invalid resize_mode '{resize_mode}'. Must be 'pad' or 'crop'."
        
        try:
            # Try with specified video filter and copying audio codec
            ffmpeg.input(video_path).output(output_video_path, vf=vf_filter, acodec='copy').run(capture_stdout=True, capture_stderr=True)
            return f"Video aspect ratio changed (audio copy) to {target_aspect_ratio} using {resize_mode}. Saved to {output_video_path}"
        except ffmpeg.Error as e_acopy:
            # Fallback to re-encoding audio if audio copy failed
            try:
                ffmpeg.input(video_path).output(output_video_path, vf=vf_filter).run(capture_stdout=True, capture_stderr=True)
                return f"Video aspect ratio changed (audio re-encoded) to {target_aspect_ratio} using {resize_mode}. Saved to {output_video_path}"
            except ffmpeg.Error as e_recode_all:
                err_acopy_msg = e_acopy.stderr.decode('utf8') if e_acopy.stderr else str(e_acopy)
                err_recode_msg = e_recode_all.stderr.decode('utf8') if e_recode_all.stderr else str(e_recode_all)
                return f"Error changing aspect ratio. Audio copy attempt failed: {err_acopy_msg}. Full re-encode attempt also failed: {err_recode_msg}."

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error changing aspect ratio: {error_message}"
    except FileNotFoundError:
        return f"Error: Input video file not found at {video_path}"
    except ValueError:
        return f"Error: Invalid target_aspect_ratio format. Expected 'num:den' (e.g., '16:9')."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# --- Granular Audio Property Tools ---
@mcp.tool()
def convert_audio_format(input_audio_path: str, output_audio_path: str, target_format: str) -> str:
    """Converts an audio file to the specified target format.
    Args:
        input_audio_path: Path to the source audio file.
        output_audio_path: Path to save the converted audio file.
        target_format: Desired output audio format (e.g., 'mp3', 'wav', 'aac').
    Returns:
        A status message indicating success or failure.
    """
    try:
        ffmpeg.input(input_audio_path).output(output_audio_path, format=target_format).run(capture_stdout=True, capture_stderr=True)
        return f"Audio format converted to {target_format} and saved to {output_audio_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error converting audio format: {error_message}"
    except FileNotFoundError:
        return f"Error: Input audio file not found at {input_audio_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def set_audio_bitrate(input_audio_path: str, output_audio_path: str, bitrate: str) -> str:
    """Sets the bitrate for an audio file.
    Args:
        input_audio_path: Path to the source audio file.
        output_audio_path: Path to save the audio file with the new bitrate.
        bitrate: Target audio bitrate (e.g., '128k', '192k', '320k').
    Returns:
        A status message indicating success or failure.
    """
    try:
        ffmpeg.input(input_audio_path).output(output_audio_path, audio_bitrate=bitrate).run(capture_stdout=True, capture_stderr=True)
        return f"Audio bitrate set to {bitrate} and saved to {output_audio_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error setting audio bitrate: {error_message}"
    except FileNotFoundError:
        return f"Error: Input audio file not found at {input_audio_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def set_audio_sample_rate(input_audio_path: str, output_audio_path: str, sample_rate: int) -> str:
    """Sets the sample rate for an audio file.
    Args:
        input_audio_path: Path to the source audio file.
        output_audio_path: Path to save the audio file with the new sample rate.
        sample_rate: Target audio sample rate in Hz (e.g., 44100, 48000).
    Returns:
        A status message indicating success or failure.
    """
    try:
        ffmpeg.input(input_audio_path).output(output_audio_path, ar=sample_rate).run(capture_stdout=True, capture_stderr=True)
        return f"Audio sample rate set to {sample_rate} Hz and saved to {output_audio_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error setting audio sample rate: {error_message}"
    except FileNotFoundError:
        return f"Error: Input audio file not found at {input_audio_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def set_audio_channels(input_audio_path: str, output_audio_path: str, channels: int) -> str:
    """Sets the number of channels for an audio file (1 for mono, 2 for stereo).
    Args:
        input_audio_path: Path to the source audio file.
        output_audio_path: Path to save the audio file with the new channel layout.
        channels: Number of audio channels (1 for mono, 2 for stereo).
    Returns:
        A status message indicating success or failure.
    """
    try:
        ffmpeg.input(input_audio_path).output(output_audio_path, ac=channels).run(capture_stdout=True, capture_stderr=True)
        return f"Audio channels set to {channels} and saved to {output_audio_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error setting audio channels: {error_message}"
    except FileNotFoundError:
        return f"Error: Input audio file not found at {input_audio_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# --- Granular Video Property Tools ---

def _run_ffmpeg_with_fallback(input_path: str, output_path: str, primary_kwargs: dict, fallback_kwargs: dict) -> str:
    """Helper to run ffmpeg command with primary kwargs, falling back to other kwargs on ffmpeg.Error."""
    try:
        ffmpeg.input(input_path).output(output_path, **primary_kwargs).run(capture_stdout=True, capture_stderr=True)
        return f"Operation successful (primary method) and saved to {output_path}"
    except ffmpeg.Error as e_primary:
        try:
            ffmpeg.input(input_path).output(output_path, **fallback_kwargs).run(capture_stdout=True, capture_stderr=True)
            return f"Operation successful (fallback method) and saved to {output_path}"
        except ffmpeg.Error as e_fallback:
            err_primary_msg = e_primary.stderr.decode('utf8') if e_primary.stderr else str(e_primary)
            err_fallback_msg = e_fallback.stderr.decode('utf8') if e_fallback.stderr else str(e_fallback)
            return f"Error. Primary method failed: {err_primary_msg}. Fallback method also failed: {err_fallback_msg}"
    except FileNotFoundError:
        return f"Error: Input file not found at {input_path}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def convert_video_format(input_video_path: str, output_video_path: str, target_format: str) -> str:
    """Converts a video file to the specified target format, attempting to copy codecs first.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the converted video file.
        target_format: Desired output video format (e.g., 'mp4', 'mov', 'avi').
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'format': target_format, 'vcodec': 'copy', 'acodec': 'copy'}
    fallback_kwargs = {'format': target_format} # Re-encode both streams
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_resolution(input_video_path: str, output_video_path: str, resolution: str) -> str:
    """Sets the resolution of a video, attempting to copy the audio stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new resolution.
        resolution: Target video resolution (e.g., '1920x1080', '1280x720', or '720' for height).
    Returns:
        A status message indicating success or failure.
    """
    vf_filters = []
    if 'x' in resolution:
        vf_filters.append(f"scale={resolution}")
    else:
        vf_filters.append(f"scale=-2:{resolution}")
    vf_filter_str = ",".join(vf_filters)
    
    primary_kwargs = {'vf': vf_filter_str, 'acodec': 'copy'}
    fallback_kwargs = {'vf': vf_filter_str} # Re-encode audio
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_codec(input_video_path: str, output_video_path: str, video_codec: str) -> str:
    """Sets the video codec of a video, attempting to copy the audio stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new video codec.
        video_codec: Target video codec (e.g., 'libx264', 'libx265', 'vp9').
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'vcodec': video_codec, 'acodec': 'copy'}
    fallback_kwargs = {'vcodec': video_codec} # Re-encode audio
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_bitrate(input_video_path: str, output_video_path: str, video_bitrate: str) -> str:
    """Sets the video bitrate of a video, attempting to copy the audio stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new video bitrate.
        video_bitrate: Target video bitrate (e.g., '1M', '2500k').
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'video_bitrate': video_bitrate, 'acodec': 'copy'}
    fallback_kwargs = {'video_bitrate': video_bitrate} # Re-encode audio
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_frame_rate(input_video_path: str, output_video_path: str, frame_rate: int) -> str:
    """Sets the frame rate of a video, attempting to copy the audio stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new frame rate.
        frame_rate: Target video frame rate (e.g., 24, 30, 60).
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'r': frame_rate, 'acodec': 'copy'}
    fallback_kwargs = {'r': frame_rate} # Re-encode audio
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_audio_track_codec(input_video_path: str, output_video_path: str, audio_codec: str) -> str:
    """Sets the audio codec of a video's audio track, attempting to copy the video stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new audio codec.
        audio_codec: Target audio codec (e.g., 'aac', 'mp3').
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'acodec': audio_codec, 'vcodec': 'copy'}
    fallback_kwargs = {'acodec': audio_codec} # Re-encode video
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_audio_track_bitrate(input_video_path: str, output_video_path: str, audio_bitrate: str) -> str:
    """Sets the audio bitrate of a video's audio track, attempting to copy the video stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new audio bitrate.
        audio_bitrate: Target audio bitrate (e.g., '128k', '192k').
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'audio_bitrate': audio_bitrate, 'vcodec': 'copy'}
    fallback_kwargs = {'audio_bitrate': audio_bitrate} # Re-encode video
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_audio_track_sample_rate(input_video_path: str, output_video_path: str, audio_sample_rate: int) -> str:
    """Sets the audio sample rate of a video's audio track, attempting to copy the video stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new audio sample rate.
        audio_sample_rate: Target audio sample rate in Hz (e.g., 44100, 48000).
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'ar': audio_sample_rate, 'vcodec': 'copy'} # ar for audio sample rate
    fallback_kwargs = {'ar': audio_sample_rate} # Re-encode video
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

@mcp.tool()
def set_video_audio_track_channels(input_video_path: str, output_video_path: str, audio_channels: int) -> str:
    """Sets the number of audio channels of a video's audio track, attempting to copy the video stream.
    Args:
        input_video_path: Path to the source video file.
        output_video_path: Path to save the video with the new audio channel layout.
        audio_channels: Number of audio channels (1 for mono, 2 for stereo).
    Returns:
        A status message indicating success or failure.
    """
    primary_kwargs = {'ac': audio_channels, 'vcodec': 'copy'} # ac for audio channels
    fallback_kwargs = {'ac': audio_channels} # Re-encode video
    return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)

# --- Phase 3: Overlays and Basic Enhancements ---

@mcp.tool()
def add_subtitles(video_path: str, srt_file_path: str, output_video_path: str, font_style: dict = None) -> str:
    """Burns subtitles from an SRT file onto a video, with optional styling.

    Args:
        video_path: Path to the input video file.
        srt_file_path: Path to the SRT subtitle file.
        output_video_path: Path to save the video with subtitles.
        font_style (dict, optional): A dictionary for subtitle styling. 
            Supported keys and example values:
            - 'font_name': 'Arial' (str)
            - 'font_size': 24 (int)
            - 'font_color': 'white' or '&H00FFFFFF' (str, FFmpeg color syntax)
            - 'outline_color': 'black' or '&H00000000' (str)
            - 'outline_width': 2 (int)
            - 'shadow_color': 'black' (str)
            - 'shadow_offset_x': 1 (int)
            - 'shadow_offset_y': 1 (int)
            - 'alignment': 7 (int, ASS alignment - Numpad layout: 1=bottom-left, 7=top-left etc. Default often 2=bottom-center)
            - 'margin_v': 10 (int, vertical margin from edge, depends on alignment)
            - 'margin_l': 10 (int, left margin)
            - 'margin_r': 10 (int, right margin)
            Default is None, which uses FFmpeg's default subtitle styling.

    Returns:
        A status message indicating success or failure.
    """
    try:
        # Basic validation for file existence
        if not os.path.exists(video_path):
            return f"Error: Input video file not found at {video_path}"
        if not os.path.exists(srt_file_path):
            return f"Error: SRT subtitle file not found at {srt_file_path}"

        input_stream = ffmpeg.input(video_path)
        
        style_args = []
        if font_style:
            if 'font_name' in font_style: style_args.append(f"FontName={font_style['font_name']}")
            if 'font_size' in font_style: style_args.append(f"FontSize={font_style['font_size']}")
            if 'font_color' in font_style: style_args.append(f"PrimaryColour={font_style['font_color']}")
            if 'outline_color' in font_style: style_args.append(f"OutlineColour={font_style['outline_color']}")
            if 'outline_width' in font_style: style_args.append(f"Outline={font_style['outline_width']}") # Outline thickness
            if 'shadow_color' in font_style: style_args.append(f"ShadowColour={font_style['shadow_color']}")
            if 'shadow_offset_x' in font_style or 'shadow_offset_y' in font_style:
                # FFmpeg 'Shadow' is more like a distance. Outline might be better for simple shadow.
                # For more control, ASS uses ShadowX, ShadowY. Let's use 'Shadow' for simplicity if only one is given.
                shadow_val = font_style.get('shadow_offset_x', font_style.get('shadow_offset_y', 1))
                style_args.append(f"Shadow={shadow_val}")
            if 'alignment' in font_style: style_args.append(f"Alignment={font_style['alignment']}")
            if 'margin_v' in font_style: style_args.append(f"MarginV={font_style['margin_v']}")
            if 'margin_l' in font_style: style_args.append(f"MarginL={font_style['margin_l']}")
            if 'margin_r' in font_style: style_args.append(f"MarginR={font_style['margin_r']}")
            # Add more style mappings as needed based on FFmpeg/ASS capabilities

        vf_filter_value = f"subtitles='{srt_file_path}'"
        if style_args:
            vf_filter_value += f":force_style='{','.join(style_args)}'"

        # Attempt to copy audio codec to speed up processing if possible
        output_stream = input_stream.output(output_video_path, vf=vf_filter_value, acodec='copy')
        try:
            output_stream.run(capture_stdout=True, capture_stderr=True)
            return f"Subtitles added successfully (audio copied) to {output_video_path}"
        except ffmpeg.Error as e_acopy:
            # Fallback to re-encoding audio if audio copy failed
            output_stream_recode_audio = input_stream.output(output_video_path, vf=vf_filter_value)
            try:
                output_stream_recode_audio.run(capture_stdout=True, capture_stderr=True)
                return f"Subtitles added successfully (audio re-encoded) to {output_video_path}"
            except ffmpeg.Error as e_recode_all:
                err_acopy_msg = e_acopy.stderr.decode('utf8') if e_acopy.stderr else str(e_acopy)
                err_recode_msg = e_recode_all.stderr.decode('utf8') if e_recode_all.stderr else str(e_recode_all)
                return f"Error adding subtitles. Audio copy attempt: {err_acopy_msg}. Full re-encode attempt: {err_recode_msg}"

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error adding subtitles: {error_message}"
    except FileNotFoundError: # This might be redundant if checked above, but good for safety.
        return f"Error: A specified file was not found."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def add_text_overlay(video_path: str, output_video_path: str, text_elements: list[dict]) -> str:
    """Adds one or more text overlays to a video at specified times and positions.

    Args:
        video_path: Path to the input main video file.
        output_video_path: Path to save the video with text overlays.
        text_elements: A list of dictionaries, where each dictionary defines a text overlay.
            Required keys for each text_element dict:
            - 'text': str - The text to display.
            - 'start_time': str or float - Start time (HH:MM:SS, or seconds).
            - 'end_time': str or float - End time (HH:MM:SS, or seconds).
            Optional keys for each text_element dict:
            - 'font_size': int (default: 24)
            - 'font_color': str (default: 'white')
            - 'x_pos': str or int (default: 'center')
            - 'y_pos': str or int (default: 'h-th-10')
            - 'box': bool (default: False)
            - 'box_color': str (default: 'black@0.5')
            - 'box_border_width': int (default: 0)
    Returns:
        A status message indicating success or failure.
    """
    try:
        if not os.path.exists(video_path):
            return f"Error: Input video file not found at {video_path}"
        if not text_elements:
            return "Error: No text elements provided for overlay."

        input_stream = ffmpeg.input(video_path)
        drawtext_filters = []

        for element in text_elements:
            text = element.get('text')
            start_time = element.get('start_time')
            end_time = element.get('end_time')

            if text is None or start_time is None or end_time is None:
                return f"Error: Text element is missing required keys (text, start_time, end_time)."
            
            # Thoroughly escape special characters in text
            # Escape single quotes, colons, commas, backslashes, and any other special chars
            safe_text = text.replace('\\', '\\\\').replace("'", "\\'").replace(':', '\\:').replace(',', '\\,')
            
            # Build filter parameters
            filter_params = [
                f"text='{safe_text}'",
                f"fontsize={element.get('font_size', 24)}",
                f"fontcolor={element.get('font_color', 'white')}",
                f"x={element.get('x_pos', '(w-text_w)/2')}",
                f"y={element.get('y_pos', 'h-text_h-10')}",
                f"enable=between(t\\,{start_time}\\,{end_time})"
            ]

            # Add box parameters if box is enabled
            if element.get('box', False):
                filter_params.append("box=1")
                filter_params.append(f"boxcolor={element.get('box_color', 'black@0.5')}")
                if 'box_border_width' in element:
                    filter_params.append(f"boxborderw={element['box_border_width']}")

            # Add font file if specified
            if 'font_file' in element:
                font_path = element['font_file'].replace('\\', '\\\\').replace("'", "\\'").replace(':', '\\:')
                filter_params.append(f"fontfile='{font_path}'")

            # Join all parameters with colons
            drawtext_filter = f"drawtext={':'.join(filter_params)}"
            drawtext_filters.append(drawtext_filter)

        # Join all drawtext filters with commas
        final_vf_filter = ','.join(drawtext_filters)

        try:
            # First attempt: try to copy audio codec
            stream = input_stream.output(output_video_path, vf=final_vf_filter, acodec='copy')
            stream.run(capture_stdout=True, capture_stderr=True)
            return f"Text overlays added successfully (audio copied) to {output_video_path}"
        except ffmpeg.Error as e_acopy:
            try:
                # Second attempt: re-encode audio if copying fails
                stream_recode = input_stream.output(output_video_path, vf=final_vf_filter)
                stream_recode.run(capture_stdout=True, capture_stderr=True)
                return f"Text overlays added successfully (audio re-encoded) to {output_video_path}"
            except ffmpeg.Error as e_recode_all:
                err_acopy_msg = e_acopy.stderr.decode('utf8') if e_acopy.stderr else str(e_acopy)
                err_recode_msg = e_recode_all.stderr.decode('utf8') if e_recode_all.stderr else str(e_recode_all)
                return f"Error adding text overlays. Audio copy attempt: {err_acopy_msg}. Full re-encode attempt: {err_recode_msg}"

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error processing text overlays: {error_message}"
    except FileNotFoundError:
        return f"Error: Input video file not found."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
def add_image_overlay(video_path: str, output_video_path: str, image_path: str, 
                        position: str = 'top_right', opacity: float = None, 
                        start_time: str = None, end_time: str = None, 
                        width: str = None, height: str = None) -> str:
    """Adds an image overlay (watermark/logo) to a video.

    Args:
        video_path: Path to the input video file.
        output_video_path: Path to save the video with the image overlay.
        image_path: Path to the image file for the overlay.
        position: Position of the overlay. 
            Options: 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'center'. 
            Or specify custom coordinates like 'x=10:y=10'.
        opacity: Opacity of the overlay (0.0 to 1.0). If None, image's own alpha is used.
        start_time: Start time for the overlay (HH:MM:SS or seconds). If None, starts from beginning.
        end_time: End time for the overlay (HH:MM:SS or seconds). If None, lasts till end.
        width: Width for the overlay image (e.g., '100', 'iw*0.1'). Original if None.
        height: Height for the overlay image (e.g., '50', 'ih*0.1'). Original if None.

    Returns:
        A status message indicating success or failure.
    """
    try:
        if not os.path.exists(video_path):
            return f"Error: Input video file not found at {video_path}"
        if not os.path.exists(image_path):
            return f"Error: Overlay image file not found at {image_path}"

        main_input = ffmpeg.input(video_path)
        overlay_input = ffmpeg.input(image_path)
        
        # Process the overlay image (scale, opacity)
        processed_overlay = overlay_input
        
        # Apply scaling if requested
        if width or height:
            scale_params = {}
            if width: scale_params['width'] = width
            if height: scale_params['height'] = height
            if width and not height: scale_params['height'] = '-1'  # Auto-height maintaining aspect
            if height and not width: scale_params['width'] = '-1'  # Auto-width maintaining aspect
            processed_overlay = processed_overlay.filter('scale', **scale_params)

        # Apply opacity if requested
        if opacity is not None and 0.0 <= opacity <= 1.0:
            # Ensure image has alpha channel, then apply opacity
            processed_overlay = processed_overlay.filter('format', 'rgba')  # Ensure alpha channel exists
            processed_overlay = processed_overlay.filter('colorchannelmixer', aa=str(opacity))

        # Determine overlay position coordinates
        overlay_x_pos = '0'
        overlay_y_pos = '0'
        if position == 'top_left':
            overlay_x_pos, overlay_y_pos = '10', '10'
        elif position == 'top_right':
            overlay_x_pos, overlay_y_pos = 'main_w-overlay_w-10', '10'
        elif position == 'bottom_left':
            overlay_x_pos, overlay_y_pos = '10', 'main_h-overlay_h-10'
        elif position == 'bottom_right':
            overlay_x_pos, overlay_y_pos = 'main_w-overlay_w-10', 'main_h-overlay_h-10'
        elif position == 'center':
            overlay_x_pos, overlay_y_pos = '(main_w-overlay_w)/2', '(main_h-overlay_h)/2'
        elif ':' in position:
            pos_parts = position.split(':')
            for part in pos_parts:
                if part.startswith('x='): overlay_x_pos = part.split('=')[1]
                if part.startswith('y='): overlay_y_pos = part.split('=')[1]

        # Prepare overlay filter parameters
        overlay_filter_kwargs = {'x': overlay_x_pos, 'y': overlay_y_pos}
        
        # Add time-based enabling condition if specified
        if start_time is not None or end_time is not None:
            actual_start_time = start_time if start_time is not None else '0'
            if end_time is not None:
                enable_expr = f"between(t,{actual_start_time},{end_time})"
            else:  # Only start_time is provided
                enable_expr = f"gte(t,{actual_start_time})"
            overlay_filter_kwargs['enable'] = enable_expr

        try:
            # Attempt 1: Create overlay with audio copying
            video_with_overlay = ffmpeg.filter([main_input, processed_overlay], 'overlay', **overlay_filter_kwargs)
            output_node = ffmpeg.output(video_with_overlay, main_input.audio, output_video_path, acodec='copy')
            output_node.run(capture_stdout=True, capture_stderr=True)
            return f"Image overlay added successfully (audio copied) to {output_video_path}"
        except ffmpeg.Error as e_acopy:
            try:
                # Attempt 2: Re-encode audio if copying fails
                # We need to reconstruct the filter chain
                video_with_overlay_fallback = ffmpeg.filter([main_input, processed_overlay], 'overlay', **overlay_filter_kwargs)
                output_node_fallback = ffmpeg.output(video_with_overlay_fallback, main_input.audio, output_video_path)
                output_node_fallback.run(capture_stdout=True, capture_stderr=True)
                return f"Image overlay added successfully (audio re-encoded) to {output_video_path}"
            except ffmpeg.Error as e_recode:
                err_acopy_msg = e_acopy.stderr.decode('utf8') if e_acopy.stderr else str(e_acopy)
                err_recode_msg = e_recode.stderr.decode('utf8') if e_recode.stderr else str(e_recode)
                return f"Error adding image overlay. Audio copy attempt: {err_acopy_msg}. Full re-encode attempt: {err_recode_msg}"

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error processing image overlay: {error_message}"
    except FileNotFoundError:
        return f"Error: An input file was not found (video: '{video_path}', image: '{image_path}'). Please check paths."
    except Exception as e:
        return f"An unexpected error occurred in add_image_overlay: {str(e)}"

# --- Phase 4: More Complex Editing & Basic AI Audio Features ---

@mcp.tool()
def concatenate_videos(video_paths: list[str], output_video_path: str,
                       transition_effect: str = None, transition_duration: float = None) -> str:
    """Concatenates multiple video files into a single output file.
    Supports optional xfade transition when concatenating exactly two videos.

    Args:
        video_paths: A list of paths to the video files to concatenate.
        output_video_path: The path to save the concatenated video file.
        transition_effect (str, optional): The xfade transition type. Options:
            - 'dissolve': Gradual blend between clips
            - 'fade': Simple fade through black
            - 'fadeblack': Fade through black
            - 'fadewhite': Fade through white
            - 'fadegrays': Fade through grayscale
            - 'distance': Distance transform transition
            - 'wipeleft', 'wiperight': Horizontal wipe
            - 'wipeup', 'wipedown': Vertical wipe
            - 'slideleft', 'slideright': Horizontal slide
            - 'slideup', 'slidedown': Vertical slide
            - 'smoothleft', 'smoothright': Smooth horizontal slide
            - 'smoothup', 'smoothdown': Smooth vertical slide
            - 'circlecrop': Rectangle crop transition
            - 'rectcrop': Rectangle crop transition
            - 'circleopen', 'circleclose': Circle open/close
            - 'vertopen', 'vertclose': Vertical open/close
            - 'horzopen', 'horzclose': Horizontal open/close
            - 'diagtl', 'diagtr', 'diagbl', 'diagbr': Diagonal transitions
            - 'hlslice', 'hrslice': Horizontal slice
            - 'vuslice', 'vdslice': Vertical slice
            - 'pixelize': Pixelize effect
            - 'radial': Radial transition
            - 'hblur': Horizontal blur
            Only applied if exactly two videos are provided. Defaults to None (no transition).
        transition_duration (float, optional): The duration of the xfade transition in seconds. 
                                             Required if transition_effect is specified. Defaults to None.
    
    Returns:
        A status message indicating success or failure.
    """
    if not video_paths:
        return "Error: No video paths provided for concatenation."
    if len(video_paths) < 1: # Allow single video to be "concatenated" (effectively copied/re-encoded)
        return "Error: At least one video is required."
    
    if transition_effect and transition_duration is None:
        return "Error: transition_duration is required when transition_effect is specified."
    if transition_effect and transition_duration <= 0:
        return "Error: transition_duration must be positive."

    # Validate transition_effect
    valid_transitions = {
        'dissolve', 'fade', 'fadeblack', 'fadewhite', 'fadegrays', 'distance',
        'wipeleft', 'wiperight', 'wipeup', 'wipedown',
        'slideleft', 'slideright', 'slideup', 'slidedown',
        'smoothleft', 'smoothright', 'smoothup', 'smoothdown',
        'circlecrop', 'rectcrop', 'circleopen', 'circleclose',
        'vertopen', 'vertclose', 'horzopen', 'horzclose',
        'diagtl', 'diagtr', 'diagbl', 'diagbr',
        'hlslice', 'hrslice', 'vuslice', 'vdslice',
        'pixelize', 'radial', 'hblur'
    }
    if transition_effect and transition_effect not in valid_transitions:
        return f"Error: Invalid transition_effect '{transition_effect}'. Valid options: {', '.join(sorted(valid_transitions))}"

    # Check if all input files exist
    for video_path in video_paths:
        if not os.path.exists(video_path):
            return f"Error: Input video file not found at {video_path}"

    # Handle single video case (copy or re-encode to target)
    if len(video_paths) == 1:
        try:
            # Simple copy if no processing needed, or re-encode to a standard format.
            # For now, let's assume re-encoding to ensure it matches expectations of a processed file.
            # This could be enhanced to use target_props like in add_b_roll if needed.
            ffmpeg.input(video_paths[0]).output(output_video_path, vcodec='libx264', acodec='aac').run(capture_stdout=True, capture_stderr=True)
            return f"Single video processed and saved to {output_video_path}"
        except ffmpeg.Error as e:
            return f"Error processing single video: {e.stderr.decode('utf8') if e.stderr else str(e)}"

    # Handle xfade transition for exactly two videos
    if transition_effect and len(video_paths) == 2:
        # Create a temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp()
        try:
            video1_path = video_paths[0]
            video2_path = video_paths[1]
            
            props1 = _get_media_properties(video1_path)
            props2 = _get_media_properties(video2_path)

            if not props1['has_video'] or not props2['has_video']:
                return "Error: xfade transition requires both inputs to be videos."
            if transition_duration >= props1['duration']:
                 return f"Error: Transition duration ({transition_duration}s) cannot be equal or longer than the first video's duration ({props1['duration']})."

            # Check if both videos have audio
            has_audio = props1['has_audio'] and props2['has_audio']
            if not has_audio:
                print("Warning: At least one video lacks audio. Xfade will be video-only or silent audio.")

            # Determine common target properties for normalization before xfade
            # Preferring higher resolution/fps from inputs, or defaulting.
            target_w = max(props1['width'], props2['width'], 640) 
            target_h = max(props1['height'], props2['height'], 360)
            # Ensure a common FPS, e.g., highest of the two, or a default like 30
            target_fps = max(props1['avg_fps'], props2['avg_fps'], 30)
            if target_fps <= 0: 
                target_fps = 30 # safety net

            # Normalize input videos to have same dimensions and properties
            # First video
            norm_video1_path = os.path.join(temp_dir, "norm_video1.mp4")
            try:
                # Scale and set properties
                subprocess.run([
                    'ffmpeg',
                    '-i', video1_path,
                    '-vf', f'scale={target_w}:{target_h}',
                    '-r', str(target_fps),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    norm_video1_path
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return f"Error normalizing first video: {e.stderr.decode('utf8') if e.stderr else str(e)}"

            # Second video
            norm_video2_path = os.path.join(temp_dir, "norm_video2.mp4")
            try:
                # Scale and set properties
                subprocess.run([
                    'ffmpeg',
                    '-i', video2_path,
                    '-vf', f'scale={target_w}:{target_h}',
                    '-r', str(target_fps),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    norm_video2_path
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                return f"Error normalizing second video: {e.stderr.decode('utf8') if e.stderr else str(e)}"

            # Get normalized video 1 duration
            norm_props1 = _get_media_properties(norm_video1_path)
            norm_video1_duration = norm_props1['duration']
            
            if transition_duration >= norm_video1_duration:
                return f"Error: Transition duration ({transition_duration}s) is too long for the normalized first video ({norm_video1_duration}s)."

            # Calculate offset (where second video starts relative to first)
            offset = norm_video1_duration - transition_duration
            
            # Create filter complex for xfade transition
            filter_complex = f"[0:v][1:v]xfade=transition={transition_effect}:duration={transition_duration}:offset={offset}"
            
            # Base command for video transition
            cmd = [
                'ffmpeg',
                '-i', norm_video1_path,
                '-i', norm_video2_path,
                '-filter_complex'
            ]
            
            # Add appropriate filters for video and audio
            if has_audio:
                # Audio transition (crossfade)
                filter_complex += f",[0:a][1:a]acrossfade=d={transition_duration}:c1=tri:c2=tri"
                cmd.extend([filter_complex, '-map', '[v]', '-map', '[a]'])
            else:
                # Video only
                filter_complex += "[v]"
                cmd.extend([filter_complex, '-map', '[v]'])
            
            # Add output file and encoding parameters
            cmd.extend([
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                output_video_path
            ])
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return f"Videos concatenated successfully with '{transition_effect}' transition to {output_video_path}"
            except subprocess.CalledProcessError as e:
                return f"Error during xfade process: {e.stderr.decode('utf8') if e.stderr else str(e)}"
                
        except Exception as e:
            return f"An unexpected error occurred during xfade concatenation: {str(e)}"
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
    
    elif transition_effect and len(video_paths) > 2:
        return f"Error: xfade transition ('{transition_effect}') is currently only supported for exactly two videos. Found {len(video_paths)} videos."

    # Standard concatenation for 2+ videos without xfade
    # We'll use the concat demuxer approach
    temp_dir = tempfile.mkdtemp()
    try:
        # Normalize all videos to the same format/codec/resolution
        normalized_paths = []
        
        # Get target properties from first video
        first_props = _get_media_properties(video_paths[0])
        target_w = first_props['width'] if first_props['width'] > 0 else 1280
        target_h = first_props['height'] if first_props['height'] > 0 else 720
        target_fps = first_props['avg_fps'] if first_props['avg_fps'] > 0 else 30
        if target_fps <= 0:
            target_fps = 30
        
        # Process each video
        for i, video_path in enumerate(video_paths):
            norm_path = os.path.join(temp_dir, f"norm_{i}.mp4")
            try:
                subprocess.run([
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', f'scale={target_w}:{target_h}',
                    '-r', str(target_fps),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    norm_path
                ], check=True, capture_output=True)
                normalized_paths.append(norm_path)
            except subprocess.CalledProcessError as e:
                return f"Error normalizing video {i}: {e.stderr.decode('utf8') if e.stderr else str(e)}"
        
        # Create a concat file
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for path in normalized_paths:
                f.write(f"file '{path}'\n")
        
        # Run ffmpeg concat
        try:
            subprocess.run([
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list_path,
                '-c', 'copy',
                '-y',
                output_video_path
            ], check=True, capture_output=True)
            return f"Videos concatenated successfully to {output_video_path}"
        except subprocess.CalledProcessError as e:
            return f"Error during concatenation: {e.stderr.decode('utf8') if e.stderr else str(e)}"
            
    except Exception as e:
        return f"An unexpected error occurred during standard concatenation: {str(e)}"
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

@mcp.tool()
def change_video_speed(video_path: str, output_video_path: str, speed_factor: float) -> str:
    """Changes the playback speed of a video (and its audio).

    Args:
        video_path: Path to the input video file.
        output_video_path: Path to save the speed-adjusted video file.
        speed_factor: The factor by which to change the speed (e.g., 2.0 for 2x speed, 0.5 for half speed).
                      Must be positive.
    
    Returns:
        A status message indicating success or failure.
    """
    if speed_factor <= 0:
        return "Error: Speed factor must be positive."
    if not os.path.exists(video_path):
        return f"Error: Input video file not found at {video_path}"

    try:
        # Process atempo values (audio speed) - requires special handling for values outside 0.5-2.0 range
        atempo_value = speed_factor
        atempo_filters = []
        
        # Handle audio speed outside atempo's range (0.5-2.0)
        if speed_factor < 0.5:
            # For speed < 0.5, use multiple atempo=0.5 filters
            while atempo_value < 0.5:
                atempo_filters.append("atempo=0.5")
                atempo_value *= 2  # After applying atempo=0.5, the remaining factor doubles
            # Add the remaining factor if needed
            if atempo_value < 0.99:  # A bit of buffer for floating point comparison
                atempo_filters.append(f"atempo={atempo_value}")
        elif speed_factor > 2.0:
            # For speed > 2.0, use multiple atempo=2.0 filters
            while atempo_value > 2.0:
                atempo_filters.append("atempo=2.0")
                atempo_value /= 2  # After applying atempo=2.0, the remaining factor halves
            # Add the remaining factor if needed
            if atempo_value > 1.01:  # A bit of buffer for floating point comparison
                atempo_filters.append(f"atempo={atempo_value}")
        else:
            # For speed factors within range, just use one atempo filter
            atempo_filters.append(f"atempo={speed_factor}")
        
        # Apply separate filters to video and audio streams
        input_stream = ffmpeg.input(video_path)
        video = input_stream.video.setpts(f"{1.0/speed_factor}*PTS")
        
        # Chain multiple audio filters if needed
        audio = input_stream.audio
        for filter_str in atempo_filters:
            audio = audio.filter("atempo", speed_factor if filter_str == f"atempo={speed_factor}" else 
                               0.5 if filter_str == "atempo=0.5" else 
                               2.0 if filter_str == "atempo=2.0" else 
                               float(filter_str.replace("atempo=", "")))
        
        # Combine processed streams and output
        output = ffmpeg.output(video, audio, output_video_path)
        output.run(capture_stdout=True, capture_stderr=True)
        
        return f"Video speed changed by factor {speed_factor} and saved to {output_video_path}"
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error changing video speed: {error_message}"
    except Exception as e:
        return f"An unexpected error occurred while changing video speed: {str(e)}"

@mcp.tool()
def remove_silence(media_path: str, output_media_path: str, 
                   silence_threshold_db: float = -30.0, 
                   min_silence_duration_ms: int = 500) -> str:
    """Removes silent segments from an audio or video file.

    Args:
        media_path: Path to the input audio or video file.
        output_media_path: Path to save the media file with silences removed.
        silence_threshold_db: The noise level (in dBFS) below which is considered silence (e.g., -30.0).
        min_silence_duration_ms: Minimum duration (in milliseconds) of silence to be removed (e.g., 500).
    
    Returns:
        A status message indicating success or failure.
    """
    if not os.path.exists(media_path):
        return f"Error: Input media file not found at {media_path}"
    if min_silence_duration_ms <= 0:
        return "Error: Minimum silence duration must be positive."

    min_silence_duration_s = min_silence_duration_ms / 1000.0

    try:
        # Step 1: Detect silence using silencedetect filter
        # The output of silencedetect is written to stderr
        silence_detection_process = (
            ffmpeg
            .input(media_path)
            .filter('silencedetect', n=f'{silence_threshold_db}dB', d=min_silence_duration_s)
            .output('-', format='null') # Output to null as we only need stderr
            .run_async(pipe_stderr=True)
        )
        _, stderr_bytes = silence_detection_process.communicate()
        stderr_str = stderr_bytes.decode('utf8')

        # Step 2: Parse silencedetect output from stderr
        silence_starts = [float(x) for x in re.findall(r"silence_start: (\d+\.?\d*)", stderr_str)]
        silence_ends = [float(x) for x in re.findall(r"silence_end: (\d+\.?\d*)", stderr_str)]
        # silencedetect might also output silence_duration, but start/end are more direct for segmenting

        if not silence_starts: # No silences detected, or only one long silence which means the file might be entirely silent or entirely loud
            # If the file is entirely silent, ffmpeg might not produce silence_start/end, or it might be one large segment.
            # A robust way to check if any sound exists might be needed if this is problematic.
            # For now, if no silences are explicitly detected, we can assume no segments need removing.
            # Or, copy the file as is.
            # Let's try to copy the file as is, as no silences were detected for removal.
            try:
                ffmpeg.input(media_path).output(output_media_path, c='copy').run(capture_stdout=True, capture_stderr=True)
                return f"No significant silences detected (or file is entirely silent/loud). Original media copied to {output_media_path}."
            except ffmpeg.Error as e_copy:
                 return f"No significant silences detected, but error copying original file: {e_copy.stderr.decode('utf8') if e_copy.stderr else str(e_copy)}"

        # Ensure starts and ends are paired correctly. Silencedetect should output them in order.
        # If there's a mismatch, it indicates a parsing error or unexpected ffmpeg output.
        if len(silence_starts) != len(silence_ends):
            # It's possible for a file to end in silence, in which case silence_end might be missing for the last detected silence_start.
            # Or start with silence, where silence_start is 0.
            # A more robust parsing might be needed if ffmpeg output varies significantly.
            # For now, we assume they are paired from the output. If not, it's an issue.
             pass # Continue and see, this might mean it ends with silence and last end is EOF

        # Get total duration of the media for the last segment
        probe = ffmpeg.probe(media_path)
        duration_str = probe['format']['duration']
        total_duration = float(duration_str)

        # Step 3: Construct segments to keep (non-silent parts)
        sound_segments = []
        current_pos = 0.0
        for i in range(len(silence_starts)):
            start_silence = silence_starts[i]
            end_silence = silence_ends[i] if i < len(silence_ends) else total_duration

            if start_silence > current_pos: # There is sound before this silence
                sound_segments.append((current_pos, start_silence))
            current_pos = end_silence # Move current position to the end of this silence
        
        if current_pos < total_duration: # There is sound after the last silence detected
            sound_segments.append((current_pos, total_duration))
        
        if not sound_segments:
            return f"Error: No sound segments were identified to keep. The media might be entirely silent according to the thresholds, or too short."

        # Step 4: Construct select filter expressions
        video_select_filter_parts = []
        audio_select_filter_parts = []
        for start, end in sound_segments:
            video_select_filter_parts.append(f'between(t,{start},{end})')
            audio_select_filter_parts.append(f'between(t,{start},{end})')

        video_select_expr = "+".join(video_select_filter_parts)
        audio_select_expr = "+".join(audio_select_filter_parts)

        # Step 5: Apply filters and output
        input_media = ffmpeg.input(media_path)
        
        has_video = any(s['codec_type'] == 'video' for s in probe['streams'])
        has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])

        output_streams = []
        if has_video:
            processed_video = input_media.video.filter('select', video_select_expr).filter('setpts', 'PTS-STARTPTS')
            output_streams.append(processed_video)
        if has_audio:
            processed_audio = input_media.audio.filter('aselect', audio_select_expr).filter('asetpts', 'PTS-STARTPTS')
            output_streams.append(processed_audio)
        
        if not output_streams:
            return "Error: The input media does not seem to have video or audio streams."

        ffmpeg.output(*output_streams, output_media_path).run(capture_stdout=True, capture_stderr=True)
        return f"Silent segments removed. Output saved to {output_media_path}"

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error removing silence: {error_message}"
    except Exception as e:
        return f"An unexpected error occurred while removing silence: {str(e)}"

# --- Phase 6: B-Roll and Basic Transitions ---

def _parse_time_to_seconds(time_str: str) -> float:
    """Converts HH:MM:SS.mmm or seconds string to float seconds."""
    if isinstance(time_str, (int, float)):
        return float(time_str)
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    return float(time_str)

def _get_media_properties(media_path: str) -> dict:
    """Probes media file and returns key properties."""
    try:
        probe = ffmpeg.probe(media_path)
        video_stream_info = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream_info = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        props = {
            'duration': float(probe['format'].get('duration', 0.0)),
            'has_video': video_stream_info is not None,
            'has_audio': audio_stream_info is not None,
            'width': int(video_stream_info['width']) if video_stream_info and 'width' in video_stream_info else 0,
            'height': int(video_stream_info['height']) if video_stream_info and 'height' in video_stream_info else 0,
            'avg_fps': 0, # Default, will be calculated if possible
            'sample_rate': int(audio_stream_info['sample_rate']) if audio_stream_info and 'sample_rate' in audio_stream_info else 44100,
            'channels': int(audio_stream_info['channels']) if audio_stream_info and 'channels' in audio_stream_info else 2,
            'channel_layout': audio_stream_info.get('channel_layout', 'stereo') if audio_stream_info else 'stereo'
        }
        if video_stream_info and 'avg_frame_rate' in video_stream_info and video_stream_info['avg_frame_rate'] != '0/0':
            num, den = map(int, video_stream_info['avg_frame_rate'].split('/'))
            if den > 0:
                props['avg_fps'] = num / den
            else:
                props['avg_fps'] = 30 # Default if denominator is 0
        else: # Fallback if avg_frame_rate is not useful
            props['avg_fps'] = 30 # A common default

        return props
    except ffmpeg.Error as e:
        raise RuntimeError(f"Error probing file {media_path}: {e.stderr.decode('utf8') if e.stderr else str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error probing file {media_path}: {str(e)}")


def _prepare_clip_for_concat(source_path: str, start_time_sec: float, end_time_sec: float,
                               target_props: dict, temp_dir: str, segment_index: int) -> str:
    """Prepares a clip segment (trims, scales, sets common properties) for concatenation.
    Returns path to the temporary processed clip.
    """
    try:
        # Create a unique temp file name
        temp_output_path = os.path.join(temp_dir, f"segment_{segment_index}.mp4")
        
        input_stream = ffmpeg.input(source_path, ss=start_time_sec, to=end_time_sec)
        
        processed_video_stream = None
        processed_audio_stream = None

        # Video processing
        if target_props['has_video']:
            video_s = input_stream.video
            video_s = video_s.filter(
                'scale',
                width=str(target_props['width']), 
                height=str(target_props['height']), 
                force_original_aspect_ratio='decrease'
            )
            video_s = video_s.filter(
                'pad',
                width=str(target_props['width']),
                height=str(target_props['height']),
                x='(ow-iw)/2',
                y='(oh-ih)/2',
                color='black'
            )
            video_s = video_s.filter('setsar', '1/1') # Use ratio e.g. 1/1 for square pixels
            video_s = video_s.filter('setpts', 'PTS-STARTPTS')
            processed_video_stream = video_s
        
        # Audio processing
        if target_props['has_audio']:
            audio_s = input_stream.audio
            audio_s = audio_s.filter('asetpts', 'PTS-STARTPTS')
            audio_s = audio_s.filter(
                'aformat',
                sample_fmts='s16', # Common format for compatibility
                sample_rates=str(target_props['sample_rate']),
                channel_layouts=target_props['channel_layout']
            )
            processed_audio_stream = audio_s

        output_params = {
            'vcodec': 'libx264',
            'pix_fmt': 'yuv420p',
            'r': target_props['avg_fps'], # Frame rate
            'acodec': 'aac',
            'ar': target_props['sample_rate'], # Audio sample rate
            'ac': target_props['channels'],   # Audio channels
            'strict': '-2' # Needed for some AAC experimental features or if defaults change
        }

        output_streams_for_ffmpeg = []
        if processed_video_stream:
            output_streams_for_ffmpeg.append(processed_video_stream)
        if processed_audio_stream:
            output_streams_for_ffmpeg.append(processed_audio_stream)
        
        if not output_streams_for_ffmpeg:
            # This can happen if the source has no video/audio or target_props indicates so.
            # For a concatenation tool, we expect valid media.
            raise ValueError(f"No video or audio streams identified to process for segment {segment_index} from {source_path}")

        ffmpeg.output(*output_streams_for_ffmpeg, temp_output_path, **output_params).run(capture_stdout=True, capture_stderr=True)
        return temp_output_path

    except ffmpeg.Error as e:
        err_msg = e.stderr.decode('utf8') if e.stderr else str(e)
        raise RuntimeError(f"Error preparing segment {segment_index} from {source_path}: {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error preparing segment {segment_index} from {source_path}: {str(e)}")

@mcp.tool()
def add_b_roll(main_video_path: str, broll_clips: list[dict], output_video_path: str) -> str:
    """Inserts B-roll clips into a main video as overlays.
    Args listed in previous messages (docstring unchanged for brevity here)
    """
    if not os.path.exists(main_video_path):
        return f"Error: Main video file not found at {main_video_path}"
    if not broll_clips:
        try:
            ffmpeg.input(main_video_path).output(output_video_path, c='copy').run(capture_stdout=True, capture_stderr=True)
            return f"No B-roll clips provided. Main video copied to {output_video_path}"
        except ffmpeg.Error as e:
            return f"No B-roll clips, but error copying main video: {e.stderr.decode('utf8') if e.stderr else str(e)}"

    valid_positions = {'fullscreen', 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'}
    valid_transitions = {'fade', 'slide_left', 'slide_right', 'slide_up', 'slide_down'}
    
    try:
        # Create a temporary directory for intermediate files
        temp_dir = tempfile.mkdtemp()
        
        try:
            main_props = _get_media_properties(main_video_path)
            if not main_props['has_video']:
                return f"Error: Main video {main_video_path} has no video stream."
                
            # Get main video dimensions 
            main_width = main_props['width']
            main_height = main_props['height']
            
            # First pass: Process each B-roll clip individually
            processed_clips = []
            
            for i, broll_item in enumerate(sorted(broll_clips, key=lambda x: _parse_time_to_seconds(x['insert_at_timestamp']))):
                clip_path = broll_item['clip_path']
                if not os.path.exists(clip_path):
                    return f"Error: B-roll clip not found at {clip_path}"
                
                broll_props = _get_media_properties(clip_path)
                if not broll_props['has_video']:
                    continue
                
                # Process timestamps
                start_time = _parse_time_to_seconds(broll_item['insert_at_timestamp'])
                duration = _parse_time_to_seconds(broll_item.get('duration', str(broll_props['duration'])))
                position = broll_item.get('position', 'fullscreen')
                
                if position not in valid_positions:
                    return f"Error: Invalid position '{position}' for B-roll {clip_path}"
                
                # Create a processed version of this clip
                temp_clip = os.path.join(temp_dir, f"processed_broll_{i}.mp4")
                scale_factor = broll_item.get('scale', 1.0 if position == 'fullscreen' else 0.5)
                
                # Apply scaling based on position
                scale_filter_parts = []
                
                if position == 'fullscreen':
                    scale_filter_parts.append(f"scale={main_width}:{main_height}")
                else:
                    scale_filter_parts.append(f"scale=iw*{scale_factor}:ih*{scale_factor}")
                
                # Add fade transitions if specified
                transition_in = broll_item.get('transition_in')
                transition_out = broll_item.get('transition_out')
                transition_duration = float(broll_item.get('transition_duration', 0.5))
                
                if transition_in == 'fade':
                    scale_filter_parts.append(f"fade=t=in:st=0:d={transition_duration}")
                
                if transition_out == 'fade':
                    # Calculate fade out start time 
                    fade_out_start = max(0, float(broll_props['duration']) - transition_duration)
                    scale_filter_parts.append(f"fade=t=out:st={fade_out_start}:d={transition_duration}")
                
                # Convert filters list to string
                filter_string = ",".join(scale_filter_parts)
                
                # Process the b-roll clip
                try:
                    subprocess.run([
                        'ffmpeg', 
                        '-i', clip_path,
                        '-vf', filter_string,
                        '-c:v', 'libx264', 
                        '-c:a', 'aac',
                        '-y',  # Overwrite output if exists
                        temp_clip
                    ], check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    return f"Error processing B-roll {i}: {e.stderr.decode('utf8') if e.stderr else str(e)}"
                
                # Calculate overlay coordinates based on position
                overlay_x = "0"
                overlay_y = "0"
                
                if position == 'top-left':
                    overlay_x, overlay_y = "10", "10" 
                elif position == 'top-right':
                    overlay_x, overlay_y = f"W-w-10", "10"  # W=main width, w=overlay width
                elif position == 'bottom-left':
                    overlay_x, overlay_y = "10", "H-h-10"  # H=main height, h=overlay height
                elif position == 'bottom-right':
                    overlay_x, overlay_y = "W-w-10", "H-h-10"
                elif position == 'center':
                    overlay_x, overlay_y = "(W-w)/2", "(H-h)/2"
                
                # Store clip info with processed path
                processed_clips.append({
                    'path': temp_clip,
                    'start_time': start_time,
                    'duration': duration,
                    'position': position,
                    'overlay_x': overlay_x,
                    'overlay_y': overlay_y,
                    'transition_in': transition_in,
                    'transition_out': transition_out,
                    'transition_duration': transition_duration,
                    'audio_mix': float(broll_item.get('audio_mix', 0.0))
                })
            
            # Second pass: Create a filter complex for all clips
            if not processed_clips:
                # No valid clips to process
                try:
                    shutil.copy(main_video_path, output_video_path)
                    return f"No valid B-roll clips to overlay. Main video copied to {output_video_path}"
                except Exception as e:
                    return f"No valid B-roll clips, but error copying main video: {str(e)}"
            
            # Build filter string for second pass
            filter_parts = []
            
            # Reference the main video
            main_overlay = "[0:v]"
            
            # Add each overlay
            for i, clip in enumerate(processed_clips):
                # Create unique labels
                current_label = f"[v{i}]"
                overlay_index = i + 1  # Start from 1 as 0 is main video
                
                # Basic overlay without slide transitions
                if not (('slide' in clip['transition_in']) or ('slide' in clip['transition_out'])):
                    # Simple overlay with enable expression
                    overlay_filter = (
                        f"{main_overlay}[{overlay_index}:v]overlay="
                        f"x={clip['overlay_x']}:y={clip['overlay_y']}:"
                        f"enable='between(t,{clip['start_time']},{clip['start_time'] + clip['duration']})'")
                    
                    if i < len(processed_clips) - 1:
                        overlay_filter += current_label
                        main_overlay = current_label
                    else:
                        # Last overlay, output directly
                        overlay_filter += "[v]"
                    
                    filter_parts.append(overlay_filter)
                else:
                    # For slide transitions, we'll use a simplified approach
                    # with basic enable condition only
                    overlay_filter = (
                        f"{main_overlay}[{overlay_index}:v]overlay="
                        f"x={clip['overlay_x']}:y={clip['overlay_y']}:"
                        f"enable='between(t,{clip['start_time']},{clip['start_time'] + clip['duration']})'")
                    
                    if i < len(processed_clips) - 1:
                        overlay_filter += current_label
                        main_overlay = current_label
                    else:
                        overlay_filter += "[v]"
                    
                    filter_parts.append(overlay_filter)
            
            # Combine filter parts
            filter_complex = ";".join(filter_parts)
            
            # Audio handling
            audio_output = []
            
            # If any clip has audio_mix > 0, we would add audio mixing here
            # For simplicity, we'll just use the main audio track
            if main_props['has_audio']:
                audio_output = ['-map', '0:a']
            
            # Prepare input files
            input_files = ['-i', main_video_path]
            for clip in processed_clips:
                input_files.extend(['-i', clip['path']])
            
            # Build the final command
            cmd = [
                'ffmpeg',
                *input_files,
                '-filter_complex', filter_complex,
                '-map', '[v]',
                *audio_output,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                output_video_path
            ]
            
            # Run final command
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return f"B-roll clips added successfully as overlays. Output at {output_video_path}"
            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode('utf8') if e.stderr else str(e)
                return f"Error in final B-roll composition: {error_message}"
        
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
    
    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error adding B-roll overlays: {error_message}"
    except ValueError as e:
        return f"Error with input values (e.g., time format): {str(e)}"
    except RuntimeError as e:
        return f"Runtime error during B-roll processing: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred in add_b_roll: {str(e)}"

@mcp.tool()
def add_basic_transitions(video_path: str, output_video_path: str, transition_type: str, duration_seconds: float) -> str:
    """Adds basic fade transitions to the beginning or end of a video.

    Args:
        video_path: Path to the input video file.
        output_video_path: Path to save the video with the transition.
        transition_type: Type of transition. Options: 'fade_in', 'fade_out'.
                         (Note: 'crossfade_from_black' is like 'fade_in', 'crossfade_to_black' is like 'fade_out')
        duration_seconds: Duration of the fade effect in seconds.
    Returns:
        A status message indicating success or failure.
    """
    if not os.path.exists(video_path):
        return f"Error: Input video file not found at {video_path}"
    if duration_seconds <= 0:
        return "Error: Transition duration must be positive."

    try:
        props = _get_media_properties(video_path)
        video_total_duration = props['duration']

        if duration_seconds > video_total_duration:
            return f"Error: Transition duration ({duration_seconds}s) cannot exceed video duration ({video_total_duration}s)."

        input_stream = ffmpeg.input(video_path)
        video_stream = input_stream.video
        audio_stream = input_stream.audio
        
        processed_video = None

        if transition_type == 'fade_in' or transition_type == 'crossfade_from_black':
            processed_video = video_stream.filter('fade', type='in', start_time=0, duration=duration_seconds)
        elif transition_type == 'fade_out' or transition_type == 'crossfade_to_black':
            fade_start_time = video_total_duration - duration_seconds
            processed_video = video_stream.filter('fade', type='out', start_time=fade_start_time, duration=duration_seconds)
        else:
            return f"Error: Unsupported transition_type '{transition_type}'. Supported: 'fade_in', 'fade_out'."

        # Attempt to copy audio, fallback to re-encoding if necessary
        output_streams = []
        if props['has_video']:
            output_streams.append(processed_video)
        if props['has_audio']:
            output_streams.append(audio_stream) # Audio is passed through without fade
        else: # Video only
            pass
        
        if not output_streams:
            return "Error: No suitable video or audio streams found to apply transition."

        try:
            ffmpeg.output(*output_streams, output_video_path, acodec='copy').run(capture_stdout=True, capture_stderr=True)
            return f"Transition '{transition_type}' applied successfully (audio copied). Output: {output_video_path}"
        except ffmpeg.Error as e_acopy:
            # Fallback: re-encode audio (or just output video if no audio originally)
            try:
                ffmpeg.output(*output_streams, output_video_path).run(capture_stdout=True, capture_stderr=True)
                return f"Transition '{transition_type}' applied successfully (audio re-encoded/processed). Output: {output_video_path}"
            except ffmpeg.Error as e_recode:
                err_acopy = e_acopy.stderr.decode('utf8') if e_acopy.stderr else str(e_acopy)
                err_recode = e_recode.stderr.decode('utf8') if e_recode.stderr else str(e_recode)
                return f"Error applying transition. Audio copy failed: {err_acopy}. Full re-encode failed: {err_recode}."

    except ffmpeg.Error as e:
        error_message = e.stderr.decode('utf8') if e.stderr else str(e)
        return f"Error applying basic transition: {error_message}"
    except ValueError as e: # For _parse_time or duration checks
        return f"Error with input values: {str(e)}"
    except RuntimeError as e: # For _get_media_properties error
        return f"Runtime error during transition processing: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred in add_basic_transitions: {str(e)}"


# Main execution block to run the server
if __name__ == "__main__":
    mcp.run() 