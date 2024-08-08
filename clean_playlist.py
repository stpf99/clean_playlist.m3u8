import requests
import m3u8
import streamlink
import argparse
from tqdm import tqdm
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

def validate_stream(url):
    """
    Validate if the provided URL is a working and active stream using streamlink.
    """
    try:
        streams = streamlink.streams(url)
        return url if 'best' in streams else None
    except Exception as e:
        print(f"Error validating stream {url}: {e}")
        return None

def load_m3u_playlist(url_or_path):
    if url_or_path.startswith(('http://', 'https://')):
        try:
            response = requests.get(url_or_path, verify=False)  # Disable SSL certificate verification
            response.raise_for_status()
            return response.text.splitlines()
        except requests.exceptions.RequestException as e:
            print(f"Error loading playlist from {url_or_path}: {e}")
            return []
    else:
        with open(url_or_path, 'r') as file:
            return file.readlines()

def parse_m3u_playlist(lines, base_url):
    urls = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            urls.append(urljoin(base_url, line))
    return urls

def extract_and_validate_playlist(url, valid_urls):
    """
    Extract and validate streams from a M3U8 playlist, handling nested playlists.
    """
    try:
        playlist = m3u8.load(url)
        base_url = url.rsplit('/', 1)[0] + '/'  # Derive base URL for resolving relative paths

        # Extract and validate segments
        for segment in playlist.segments:
            if segment.uri:
                valid_urls.append(urljoin(base_url, segment.uri))

        # Handle nested playlists
        for playlist in playlist.playlists:
            if playlist.uri:
                nested_url = urljoin(base_url, playlist.uri)
                extract_and_validate_playlist(nested_url, valid_urls)

    except Exception as e:
        print(f"Error processing playlist {url}: {e}")

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

def validate_streams_in_batches(urls, batch_size=10):
    """
    Validate streams in batches using threading for improved performance.
    """
    valid_streams = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(validate_stream, url): url for url in urls}

        for future in tqdm(as_completed(future_to_url), total=len(future_to_url), desc="Validating streams", unit="stream"):
            result = future.result()
            if result:
                valid_streams.append(result)

    return valid_streams

def validate_m3u(url_or_path):
    """
    Validate the streams in the provided M3U playlist URL or file path.
    """
    try:
        lines = load_m3u_playlist(url_or_path)
        base_url = url_or_path if url_or_path.startswith(('http://', 'https://')) else ''
        urls = parse_m3u_playlist(lines, base_url)

        valid_streams = validate_streams_in_batches(urls, batch_size=10)

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
