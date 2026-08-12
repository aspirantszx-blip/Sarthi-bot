import requests
import json
import os
import re
import sys

BASE_URL = "https://api.penpencil.co"

def get_headers(token):
    """Generates standard authorization and contextual headers."""
    if not token.startswith("Bearer "):
        token = f"Bearer {token}"
    return {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.pw.live/",
        "Origin": "https://www.pw.live",
        "Accept": "application/json, text/plain, */*"
    }

def fetch_my_batches(session, headers):
    """Fetches registered user batches with an automated fallback mechanism."""
    url = f"{BASE_URL}/v3/my-batches?page=1&limit=50"
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {}).get('batches', [])
    except requests.RequestException:
        pass

    # Fallback to the explicit cohort widget configuration endpoint
    fallback_url = f"{BASE_URL}/v3/cohort/69b3af0500ddd0a1aa733fe5/widgets/all-courses"
    try:
        response = session.get(fallback_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', [])
    except requests.RequestException:
        pass
    
    return None

def get_real_video_link(session, video_id, headers):
    """Resolves stream tracks dynamically or defaults to standard CDN path mapping."""
    endpoints = [
        f"{BASE_URL}/v3/videos/{video_id}",
        f"{BASE_URL}/v2/videos/{video_id}"
    ]
    for url in endpoints:
        try:
            res = session.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get('data', {})
                stream_url = data.get('hlsUrl') or data.get('url') or data.get('videoUrl') or data.get('masterUrl')
                if stream_url:
                    return stream_url
        except requests.RequestException:
            continue
            
    # Default Cloudflare/Cloudfront streaming track delivery fallback
    return f"https://d1d34p8vz63oiq.cloudfront.net/{video_id}/master.mpd"

def fetch_batch_contents(session, batch_id, slug, content_type, headers):
    """Queries structural data based on standard classification indexes."""
    url = f"{BASE_URL}/v2/batches/{batch_id}/subject/{slug}/contents?page=1&contentType={content_type}&limit=100"
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', [])
    except requests.RequestException:
        pass
    return []

def main():
    print("==================================================")
    print("     PROFESSIONAL CLASSROOM LINK EXPORTER         ")
    print("==================================================\n")
    
    token = input("👉 Please enter your Bearer Token:\n").strip()
    if not token:
        print("❌ Error: Bearer Token verification failed. Input string is empty.")
        return
        
    headers = get_headers(token)
    
    # Session instantiation facilitates faster extraction due to connection pooling
    with requests.Session() as session:
        batches = fetch_my_batches(session, headers)
        
        if not batches:
            print("❌ Error: Unable to access courses. Check network state or token validity.")
            return
            
        print(f"\n✅ Found {len(batches)} Batches linked to this profile:\n")
        for idx, batch in enumerate(batches, start=1):
            name = batch.get('name') or batch.get('typeInfo', {}).get('name', 'Unknown Batch')
            print(f"[{idx}] {name}")
            
        try:
            choice = int(input("\n👉 Select Batch S.No to process: "))
            selected_batch = batches[choice - 1]
        except (ValueError, IndexError):
            print("❌ Error: Invalid numerical selection indicator entered.")
            return
            
        batch_id = selected_batch.get('_id') or selected_batch.get('typeId')
        batch_name = selected_batch.get('name') or selected_batch.get('typeInfo', {}).get('name', 'Batch')
        
        # Format a secure file name string matching directory parameters
        clean_name = re.sub(r'[\\/*?:"<>|]', "", batch_name)[:50]
        output_file = f"{clean_name}.txt"
        
        print(f"\n⏳ Querying structures... Generating index database inside '{output_file}'...")
        
        details_res = session.get(f"{BASE_URL}/v3/batches/{batch_id}/details", headers=headers, timeout=10)
        if details_res.status_code != 200:
            print("❌ Error: High-level database request for selected classroom configuration failed.")
            return
            
        subjects = details_res.json().get('data', {}).get('subjects', [])
        
        with open(output_file, "w", encoding="utf-8") as txt_file:
            for sub in subjects:
                sub_name = sub.get('subject')
                sub_slug = sub.get('slug')
                
                print(f"🔄 Parsing Index Segment: {sub_name}")
                
                # 1. LECTURE VIDEO DECODER LINK RESOLUTION
                lectures = fetch_batch_contents(session, batch_id, sub_slug, "lectures", headers)
                if lectures:
                    for lec in lectures:
                        topic = lec.get('topic', 'Untitled Lesson')
                        v_id = lec.get('videoDetails', {}).get('id', '')
                        if v_id:
                            video_url = get_real_video_link(session, v_id, headers)
                            txt_file.write(f"({sub_name}) {topic}:{video_url}\n")
                
                # 2. DOCUMENT RESOURCE RECOVERY (Dynamic Path Construction)
                notes = fetch_batch_contents(session, batch_id, sub_slug, "notes", headers)
                if notes:
                    for item in notes:
                        for homework in item.get('homeworkIds', []):
                            topic = homework.get('topic', 'Untitled Resource')
                            for attachment in homework.get('attachmentIds', []):
                                base_url = attachment.get('baseUrl', 'https://static.pw.live/')
                                raw_name = attachment.get('name', '')
                                if raw_name:
                                    # Dynamically link paths depending on the structural return format of the database
                                    if raw_name.startswith("http"):
                                        resolved_url = raw_name.replace(" ", "%20")
                                    else:
                                        resolved_url = f"{base_url}{raw_name}".replace(" ", "%20")
                                        
                                    txt_file.write(f"({sub_name}) {topic}:{resolved_url}\n")
                                    
        print(f"\n🏆 Success: Reference tracking indexes exported cleanly.")
        print(f"📁 Document File Location: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    main()