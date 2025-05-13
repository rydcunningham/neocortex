import json
import os
import urllib.request
import podcastparser
import datetime
from typing import Dict, List, Set

def get_project_root() -> str:
    """Get root directory path"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_tracked_podcasts() -> Dict:
    """Load the tracked podcasts configuration"""
    root_dir = get_project_root()
    config_path = os.path.join(root_dir, 'sample_drive', 'metadata', 'podcasts', 'tracked_podcasts.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def load_podcast_metadata() -> Dict:
    """Load or create the podcast metadata file"""
    root_dir = get_project_root()
    metadata_file = os.path.join(root_dir, 'sample_drive', 'metadata', 'podcasts', 'podcasts_metadata.json')
    
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            return json.load(f)
    else:
        # Create initial metadata structure
        return {
            "last_check": "",
            "processed_episodes": {}
        }

def save_podcast_metadata(metadata: Dict) -> None:
    """Save updated metadata"""
    root_dir = get_project_root()
    metadata_file = os.path.join(root_dir, 'sample_drive', 'metadata', 'podcasts', 'podcasts_metadata.json')
    
    # Ensure metadata directory exists
    os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def create_opener():
    """Create URL opener with proper headers"""
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'),
        ('Accept', 'application/rss+xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,*/*;q=0.7'),
    ]
    return opener

def main():
    # Load configurations
    tracked_podcasts = load_tracked_podcasts()
    metadata = load_podcast_metadata()
    
    # Get set of processed episodes
    processed_episodes = set(metadata['processed_episodes'].keys())
    
    # Track new episodes
    new_episodes = []
    
    # Update last check time
    metadata['last_check'] = datetime.datetime.now().isoformat()
    
    # Create URL opener with headers
    opener = create_opener()

    # Check each podcast feed
    for podcast in tracked_podcasts['podcasts']:
        if not podcast['transcribe']:
            continue
            
        print(f"\nChecking feed for: {podcast['name']}")
        try:
            response = opener.open(podcast['rss_url'])
            parsed = podcastparser.parse(podcast['rss_url'], response)
            
            # Process each episode in the feed
            for episode in parsed['episodes']:
                # Create unique identifier for episode
                episode_id = f"{podcast['name']}_{episode['guid']}"
                
                if episode_id not in processed_episodes:
                    new_episode = {
                        'podcast_name': podcast['name'],
                        'episode_title': episode['title'],
                        'episode_id': episode_id,
                        'published': episode['published'],
                        'duration': episode.get('duration', 0),
                        'enclosure_url': episode.get('enclosures', [{}])[0].get('url', ''),
                        'description': episode.get('description', '')
                    }
                    new_episodes.append(new_episode)
            
            if new_episodes:
                print(f"Found {len(new_episodes)} new episodes")
            else:
                print("No new episodes found")
                
        except urllib.error.HTTPError as e:
            print(f"HTTP Error for {podcast['name']}: {e.code} - {e.reason}")
            continue
        except urllib.error.URLError as e:
            print(f"URL Error for {podcast['name']}: {str(e)}")
            continue
        except Exception as e:
            print(f"Error processing feed {podcast['name']}: {str(e)}")
            continue
    
    # Update metadata with new episodes
    for episode in new_episodes:
        metadata['processed_episodes'][episode['episode_id']] = {
            'podcast_name': episode['podcast_name'],
            'episode_title': episode['episode_title'],
            'published': episode['published'],
            'duration': episode['duration'],
            'enclosure_url': episode['enclosure_url'],
            'processed_date': None,
            'transcription_file': None,
            'status': 'pending'
        }
    
    # Save updated metadata
    save_podcast_metadata(metadata)
    
    # Print summary
    print(f"\nFound {len(new_episodes)} total new episodes to process")
    for episode in new_episodes:
        print(f"\n{episode['podcast_name']}: {episode['episode_title']}")
        print(f"Published: {datetime.datetime.fromtimestamp(episode['published'])}")

if __name__ == "__main__":
    main()
