import os
import sys
import mlx_whisper
import re
import urllib.request
import json
from typing import Dict, Optional
from pathlib import Path
import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def get_project_root() -> str:
    """Get root directory path"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_podcast_metadata() -> Dict:
    """Load podcast metadata file"""
    root_dir = get_project_root()
    metadata_file = os.path.join(root_dir, 'sample_drive', 'metadata', 'podcasts', 'podcasts_metadata.json')
    with open(metadata_file, 'r') as f:
        return json.load(f)

def save_podcast_metadata(metadata: Dict) -> None:
    """Save updated metadata"""
    root_dir = get_project_root()
    metadata_file = os.path.join(root_dir, 'sample_drive', 'metadata', 'podcasts', 'podcasts_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def create_safe_filename(title: str) -> str:
    """Create a safe, lowercase, underscore-joined filename from a title"""
    # Convert to lowercase and replace spaces/special chars with underscores
    safe_name = title.lower()
    safe_name = re.sub(r'[^\w\s-]', '', safe_name)  # Remove special characters
    safe_name = re.sub(r'[-\s]+', '_', safe_name)   # Replace spaces and hyphens with underscore
    return safe_name.strip('_')  # Remove leading/trailing underscores

def download_episode(episode: Dict, podcast_name: str, episode_id: str) -> Optional[str]:
    """Download episode MP3 to appropriate folder"""
    root_dir = get_project_root()
    audio_dir = os.path.join(root_dir, 'sample_drive', 'inbox', 'podcasts', 'audio', podcast_name)
    os.makedirs(audio_dir, exist_ok=True)
    
    try:
        # Create safe filename from episode title
        safe_filename = create_safe_filename(episode['episode_title'])
        audio_file = os.path.join(audio_dir, f"{safe_filename}.mp3")
        
        # Download the file
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(episode['enclosure_url'], audio_file)
        
        return audio_file
    except Exception as e:
        print(f"Error downloading {episode['episode_title']}: {str(e)}")
        return None

def transcribe_audio(audio_file: str, podcast_name: str) -> Optional[str]:
    """Transcribe audio file using MLX Whisper"""
    root_dir = get_project_root()
    transcript_dir = os.path.join(root_dir, 'sample_drive', 'inbox', 'podcasts', 'transcripts', podcast_name)
    os.makedirs(transcript_dir, exist_ok=True)
    
    try:
        # Start transcription
        relative_audio_path = os.path.relpath(audio_file, root_dir)
        logger.info(f"Starting transcription of {relative_audio_path}")
        start_time = datetime.datetime.now()
        
        # Transcribe with mlx-whisper
        result = mlx_whisper.transcribe(
            audio_file, 
            path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            verbose=False  # Disable verbose output since we're using tqdm
        )
        
        # Calculate and log duration
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"Transcription completed in {duration.total_seconds():.2f} seconds")
        
        # Create transcript filename using same base name as audio file
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        transcript_file = os.path.join(transcript_dir, f"{base_name}.txt")
        
        # Save transcript
        logger.info("Saving transcript...")
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        
        relative_transcript_path = os.path.relpath(transcript_file, root_dir)
        logger.info(f"Transcript saved to {relative_transcript_path}")
        return transcript_file
        
    except Exception as e:
        logger.error(f"Error transcribing {os.path.basename(audio_file)}: {str(e)}")
        return None

def cleanup_audio(audio_file: str) -> None:
    """Delete audio file after successful transcription"""
    try:
        os.remove(audio_file)
    except Exception as e:
        print(f"Error deleting {audio_file}: {str(e)}")

def process_episode(episode_id: str, episode_data: Dict, metadata: Dict) -> bool:
    """
    Process a single episode from download through transcription.
    Returns True if successful, False otherwise.
    """
    root_dir = get_project_root()
    print(f"\nProcessing: {episode_data['episode_title']}")
    
    try:
        # Download audio
        audio_file = download_episode(episode_data, episode_data['podcast_name'], episode_id)
        if not audio_file:
            metadata['processed_episodes'][episode_id]['status'] = 'failed'
            return False
        
        # Transcribe
        transcript_file = transcribe_audio(audio_file, episode_data['podcast_name'])
        if not transcript_file:
            metadata['processed_episodes'][episode_id]['status'] = 'failed'
            cleanup_audio(audio_file)
            return False
        
        # Update metadata with relative path using consistent filename format
        relative_transcript_path = os.path.relpath(transcript_file, root_dir)
        
        metadata['processed_episodes'][episode_id].update({
            'processed_date': datetime.datetime.now().isoformat(),
            'transcription_file': relative_transcript_path,
            'status': 'completed'
        })
        
        # Cleanup
        cleanup_audio(audio_file)
        print(f"Successfully processed {episode_data['episode_title']}")
        return True
        
    except Exception as e:
        print(f"Error processing {episode_data['episode_title']}: {str(e)}")
        metadata['processed_episodes'][episode_id]['status'] = 'failed'
        return False

def process_pending_episodes(batch_size: int = 5, max_episodes: Optional[int] = None):
    """Process pending episodes in batches"""
    metadata = load_podcast_metadata()
    
    # Get pending episodes
    pending_episodes = [
        (ep_id, ep_data) for ep_id, ep_data in metadata['processed_episodes'].items()
        if ep_data['status'] == 'pending'
    ]
    
    print(f"Found {len(pending_episodes)} pending episodes")
    
    if max_episodes is not None:
        if len(pending_episodes) > max_episodes:
            pending_episodes = pending_episodes[:max_episodes]
            print(f"Limiting to {max_episodes} episodes")
    
    # Process in batches
    for i in range(0, len(pending_episodes), batch_size):
        batch = pending_episodes[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}")
        
        for episode_id, episode_data in batch:
            success = process_episode(episode_id, episode_data, metadata)
            # Save metadata after each episode regardless of success
            save_podcast_metadata(metadata)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Transcribe podcast episodes')
    parser.add_argument('--batch-size', type=int, default=5,
                      help='Number of episodes to process in each batch')
    parser.add_argument('--max-episodes', type=int, default=20,
                      help='Limit the number of episodes to process')
    parser.add_argument('--episode-id', type=str,
                      help='Process specific episode by ID')
    args = parser.parse_args()
    
    if args.episode_id:
        # Process single episode
        metadata = load_podcast_metadata()
        if args.episode_id in metadata['processed_episodes']:
            success = process_episode(
                args.episode_id, 
                metadata['processed_episodes'][args.episode_id],
                metadata
            )
            save_podcast_metadata(metadata)
            sys.exit(0 if success else 1)
        else:
            print(f"Episode ID {args.episode_id} not found in metadata")
            sys.exit(1)
    else:
        # Process pending episodes in batches
        process_pending_episodes(args.batch_size, args.max_episodes)

if __name__ == "__main__":
    main()