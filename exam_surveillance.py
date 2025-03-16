import cv2
import os
import google.generativeai as genai
from datetime import timedelta
from PIL import Image
import io
from dotenv import load_dotenv
import json
from datetime import datetime
import requests
import base64
from telegram_notifier import send_summary

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_FLASH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

def encode_image_to_base64(pil_image):
    """Convert PIL Image to base64 string."""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def extract_frames(video_path, interval_seconds=60):
    """Extract frames from video at specified interval."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Error: Could not open video file")

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * interval_seconds)
    
    frames = []
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            # Convert frame from BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp = timedelta(seconds=int(frame_count/fps))
            frames.append((frame_rgb, timestamp))
            
        frame_count += 1
    
    cap.release()
    return frames

def analyze_frame(frame, timestamp):
    """Analyze a frame using Gemini Flash 2.0 API."""
    # Convert numpy array to PIL Image and resize if needed
    pil_image = Image.fromarray(frame)
    
    # Resize image if too large (max 4MB)
    max_size = (1024, 1024)
    pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert image to base64
    image_base64 = encode_image_to_base64(pil_image)
    
    # Create the request payload
    payload = {
        "contents": [{
            "parts":[{
                "text": """Analyze this exam hall image and identify any suspicious behavior or disciplinary issues. 
                Look for:
                1. Students looking at others' papers
                2. Use of unauthorized materials
                3. Communication between students
                4. Use of mobile phones or other electronic devices
                5. Any other suspicious or concerning behavior
                
                Provide a detailed analysis of any suspicious activities found, or confirm if everything appears normal."""
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }
            }]
        }]
    }
    
    # Make the API request
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }
    
    response = requests.post(GEMINI_FLASH_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        # Extract the text from the response
        analysis_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No analysis available')
    else:
        analysis_text = f"Error analyzing frame: {response.status_code} - {response.text}"
    
    return {
        'timestamp': str(timestamp),
        'analysis': analysis_text
    }

def main():
    # Create output directory for results
    output_dir = 'analysis_results'
    os.makedirs(output_dir, exist_ok=True)
    
    # Process video
    video_path = 'exam_video.mp4'  # Update this with your video path
    print(f"Processing video: {video_path}")
    
    try:
        # Extract frames
        frames = extract_frames(video_path)
        print(f"Extracted {len(frames)} frames")
        
        # Analyze each frame
        results = []
        for i, (frame, timestamp) in enumerate(frames):
            print(f"Analyzing frame {i+1}/{len(frames)} at timestamp {timestamp}")
            analysis = analyze_frame(frame, timestamp)
            results.append(analysis)
            
            # Save frame as image
            frame_filename = f"frame_{timestamp}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            Image.fromarray(frame).save(frame_path)
        
        # Save results to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(output_dir, f'analysis_results_{timestamp}.json')
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=4)
            
        print(f"\nAnalysis complete! Results saved to {results_file}")
        print(f"Frames saved in {output_dir}")
        
        # Send analysis summary to Telegram
        print("Sending analysis summary to Telegram...")
        import asyncio
        from telegram_notifier import TelegramNotifier

        async def send_results_one_by_one(results_file_path):
            # Load the analysis results from the JSON file
            with open(results_file_path, 'r') as f:
                analysis_entries = json.load(f)
            # Create a single notifier instance to reuse for all messages
            notifier = TelegramNotifier()
            # Iterate over each analysis entry and send it individually
            for entry in analysis_entries:
                timestamp = entry.get("timestamp", "N/A")
                analysis = entry.get("analysis", "No analysis available")
                # Format the message with HTML styling
                message = (
                    f"<b>Frame Analysis</b>\n"
                    f"<b>Timestamp:</b> {timestamp}\n"
                    f"<b>Analysis:</b> {analysis}"
                )
                await notifier.send_message(message)
                await asyncio.sleep(1)  # Small delay between messages to avoid rate limits

        asyncio.run(send_results_one_by_one(results_file))
        # send_summary(results_file)
        print("Summary sent to Telegram!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()