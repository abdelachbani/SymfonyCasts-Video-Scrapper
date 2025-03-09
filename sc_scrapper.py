#!/usr/bin/env python3
import requests
import xml.etree.ElementTree as ET
import os
import sys

if len(sys.argv) < 2:
    print("Use: python script.py <course_base_url>")
    sys.exit(1)

course_base_url = sys.argv[1].rstrip('/')
SITEMAP_URL = "https://symfonycasts.com/sitemap.default.xml"
if len(sys.argv) == 3:
    OUTPUT_FOLDER = sys.argv[2]
else:
    OUTPUT_FOLDER = ""

# Auth session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0"
})

session.cookies.update({
    # Auth cookies go here
})

response = session.get(SITEMAP_URL)
if response.status_code != 200:
    print("Not able to find the sitemap.")
    sys.exit(1)

root = ET.fromstring(response.text)
namespaces = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

course_paths = []
for url in root.findall("ns:url", namespaces):
    loc = url.find("ns:loc", namespaces).text
    if loc.startswith(course_base_url):
        remainder = loc[len(course_base_url):]
        if remainder and remainder[0] != "/":
            continue  # It's not in the searched course.
        relative = remainder.strip('/')
        if relative and "/activity/" not in remainder:
            course_paths.append(relative)

for i, video_name in enumerate(course_paths):
    video_url = f"{course_base_url}/{video_name}/download/video"
    subtitles_url = f"{course_base_url}/{video_name}/download/subtitles"
    
    # Create a folder for each video, starting from the path of the output folder specified in the command line.
    video_folder = OUTPUT_FOLDER+f"{i+1}.{video_name}"
    os.makedirs(video_folder, exist_ok=True)
    
    video_path = os.path.join(video_folder, f"{i+1}. {video_name}.mp4")
    subtitles_path = os.path.join(video_folder, f"{i+1}. {video_name}.vtt")
    
    print(f"Downloading video from {video_url}...")
    video_response = session.get(video_url, stream=True)
    if video_response.status_code == 200:
        content_type = video_response.headers.get("Content-Type", "")
        if "video" not in content_type:
            print(f"Error: {video_url} didn't return a video file (Content-Type: {content_type}).")
        else:
            with open(video_path, "wb") as file:
                for chunk in video_response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            print(f"Downloaded: {video_path}")
    else:
        print(f"Error downloading {video_url} (HTTP {video_response.status_code})")
    
    print(f"Downloading subtitles from {subtitles_url}...")
    subtitles_response = session.get(subtitles_url, stream=True)
    if subtitles_response.status_code == 200:
        content_type = subtitles_response.headers.get("Content-Type", "")
        # Generally subtitles have a content-type "text" or "application" (not sure lol).
        if "text" not in content_type and "application" not in content_type:
            print(f"Error: {subtitles_url} didn't return a subtitles file (Content-Type: {content_type}).")
        else:
            # First line of SymfonyCasts subtitles is always "WEBVTT" (at the moment of this being written).
            lines = subtitles_response.iter_lines(decode_unicode=True)
            try:
                first_line = next(lines).strip()
            except StopIteration:
                print("Empty subtitles.")
                continue
            if first_line != "WEBVTT":
                print(f"Subtitles in {subtitles_url} do not start with 'WEBVTT'. The download has been cancelled.")
                continue

            with open(subtitles_path, "w", encoding="utf-8") as file:
                file.write(first_line + "\n")
                for line in lines:
                    file.write(line + "\n")
            print(f"Downloaded subtitles: {subtitles_path}")
    else:
        print(f"Error downloading the subtitles {subtitles_url} (HTTP {subtitles_response.status_code})")
