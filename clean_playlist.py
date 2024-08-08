import sys
import vlc
import os
import requests
import argparse
from tqdm import tqdm  # Biblioteka do wskaźników postępu

def create_vlc_instance():
    # Inicjalizowanie instancji VLC z opcjami
    vlc_instance = vlc.Instance('--no-xlib --aout=alsa')
    return vlc_instance

def validate_stream(url):
    """
    Validate if the provided URL is a working stream.
    """
    try:
        vlc_instance = create_vlc_instance()
        player = vlc.MediaPlayer(vlc_instance, url)
        media = player.get_media()
        media.parse()  # Parse the media to check if it loads correctly
        if media.get_state() == vlc.State.Error:
            return False
        return True
    except Exception as e:
        print(f"Error validating stream {url}: {e}")
        return False

def load_m3u_playlist(url_or_path):
    if url_or_path.startswith(('http://', 'https://')):
        response = requests.get(url_or_path)
        response.raise_for_status()
        return response.text.splitlines()
    else:
        with open(url_or_path, 'r') as file:
            return file.readlines()

def parse_m3u_playlist(lines):
    urls = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            urls.append(line)
    return urls

def save_valid_playlist(input_lines, valid_urls, file_path):
    with open(file_path, 'w') as file:
        for line in input_lines:
            if line.strip() and not line.startswith('#'):
                if line.strip() in valid_urls:
                    file.write(f"{line}\n")
                else:
                    print(f"Invalid stream: {line.strip()}")
            else:
                file.write(f"{line}\n")
    print(f"Saved {len(valid_urls)} valid streams to {file_path}")

def validate_m3u(url_or_path):
    """
    Validate the streams in the provided M3U playlist URL or file path.
    """
    try:
        lines = load_m3u_playlist(url_or_path)
        urls = parse_m3u_playlist(lines)

        valid_streams = []

        # Use tqdm for progress bar
        for url in tqdm(urls, desc="Validating streams", unit="stream"):
            if validate_stream(url):
                valid_streams.append(url)

        return lines, valid_streams
    except Exception as e:
        print(f"Error loading or parsing M3U playlist: {e}")
        return [], []

def main():
    parser = argparse.ArgumentParser(description='Validate M3U/M3U8 playlists.')
    parser.add_argument('source', type=str, help='URL or path to the M3U/M3U8 playlist')
    parser.add_argument('--output', type=str, help='Path to save valid streams')

    args = parser.parse_args()

    input_lines, valid_streams = validate_m3u(args.source)

    if args.output:
        save_valid_playlist(input_lines, valid_streams, args.output)
    else:
        print("Valid streams:")
        for stream in valid_streams:
            print(stream)

if __name__ == "__main__":
    main()
