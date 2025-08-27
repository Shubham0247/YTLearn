import os
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import re


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL using multiple methods."""
    try:
        # Method 1: Using regex (most reliable)
        video_id_match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})', url)
        if video_id_match:
            return video_id_match.group(1)
        
        # Method 2: Using urllib.parse as fallback
        parsed_url = urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        elif parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
        
        raise ValueError("Could not extract video ID from URL")
    except Exception as e:
        raise Exception(f"Error extracting video ID: {str(e)}")


def get_video_title(url: str) -> str:
    """Get YouTube video title using yt-dlp."""
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,  # Suppress output
            'no_warnings': True,
            'extractaudio': False,
            'format': 'worst',  # We only need metadata, not the actual video
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            if not title or title == 'Unknown Title':
                raise ValueError("Could not extract video title")
            return title
            
    except Exception as e:
        # If yt-dlp fails, try to extract video ID and create a basic title
        try:
            video_id = extract_video_id(url)
            return f"YouTube Video ({video_id})"
        except:
            raise Exception(f"Error getting video title: {str(e)}")


def get_video_transcript(url: str) -> str:
    """Get YouTube video transcript using the latest API methods with fetch()."""
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Get the list of available transcripts
        try:
            transcript_list = YouTubeTranscriptApi().list(video_id)

        except Exception as e:
            raise Exception(f"Could not retrieve transcript list: {str(e)}. This video may not have captions available.")
        
        transcript_data = None
        
        # Strategy 1: Try to find manually created English transcripts first
        for transcript in transcript_list:
            if transcript.language_code.startswith('en') and not transcript.is_generated:

                transcript_data = transcript.fetch()
                break
        
        # Strategy 2: Try auto-generated English transcripts
        if not transcript_data:
            for transcript in transcript_list:
                if transcript.language_code.startswith('en') and transcript.is_generated:
    
                    transcript_data = transcript.fetch()
                    break
        
        # Strategy 3: Try to translate any available transcript to English
        if not transcript_data:
            for transcript in transcript_list:
                try:
                    if transcript.is_translatable:

                        transcript_data = transcript.translate('en').fetch()
                        break
                except Exception as e:

                    continue
        
        # Strategy 4: Use any available transcript as last resort
        if not transcript_data:
            for transcript in transcript_list:
                try:

                    transcript_data = transcript.fetch()
                    break
                except Exception as e:

                    continue
        
        # Check if we got any transcript data
        if not transcript_data:
            raise Exception("Could not retrieve any transcript. This video may not have captions available.")
        
        # Process transcript data
        if not transcript_data or len(transcript_data) == 0:
            raise ValueError("No transcript data available for this video")
            
        # Join transcript entries and clean up
        # The transcript_data contains FetchedTranscriptSnippet objects with .text attribute
        transcript = " ".join([entry.text for entry in transcript_data])
        
        # Advanced cleanup
        transcript = transcript.replace('\n', ' ')
        transcript = re.sub(r'\s+', ' ', transcript)  # Replace multiple spaces with single space
        transcript = transcript.strip()
        
        if len(transcript) < 10:
            raise ValueError("Transcript is too short or empty")
        

        return transcript
        
    except Exception as e:
        raise Exception(f"Error getting video transcript: {str(e)}")