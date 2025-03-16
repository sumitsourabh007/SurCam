import cv2
import os
import time
import logging
import urllib.parse
import google.generativeai as genai
from datetime import datetime, timedelta
from PIL import Image
import io
import json
import base64
import requests
from dotenv import load_dotenv
from telegram_notifier import TelegramNotifier
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("camera_surveillance.log"),
        logging.StreamHandler()
    ]
)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_FLASH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

class CameraSurveillance:
    def __init__(self, camera_ip, username, password, port=554, channel=1, output_dir="surveillance_images"):
        """
        Initialize the camera surveillance system.
        
        Args:
            camera_ip (str): IP address of the camera.
            username (str): Camera login username.
            password (str): Camera login password.
            port (int): RTSP port (default: 554).
            channel (int): Camera channel number (default: 1).
            output_dir (str): Directory to save captured images.
        """
        self.camera_ip = camera_ip
        self.username = urllib.parse.quote(username)
        self.password = urllib.parse.quote(password)
        self.port = port
        self.channel = channel
        self.output_dir = output_dir
        self.analysis_dir = "analysis_results"
        self.cap = None
        self.telegram = TelegramNotifier()

        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)

        # Define multiple RTSP URL formats
        self.rtsp_urls = [
            f"rtsp://{self.username}:{self.password}@{camera_ip}:{port}/h264/ch{channel}/main/av_stream",
            f"rtsp://{self.username}:{self.password}@{camera_ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
            f"rtsp://{self.username}:{self.password}@{camera_ip}:{port}/Streaming/Channels/{channel}01",
            f"rtsp://{self.username}:{self.password}@{camera_ip}:{port}/live/ch{channel}/main"
        ]
    
    def connect(self):
        """
        Try connecting to the camera using different RTSP URL formats.
        
        Returns:
            bool: True if connection successful and a test frame is retrieved, False otherwise.
        """
        for url in self.rtsp_urls:
            try:
                logging.info(f"Attempting to connect using URL: {url}")
                
                # Set FFmpeg options for better streaming
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|buffer_size;512000|max_delay;500000"
                
                # Create VideoCapture object with FFmpeg backend
                self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Set buffer size
                
                if self.cap is None or not self.cap.isOpened():
                    logging.warning(f"Failed to open video capture for URL: {url}")
                    continue
                    
                # Try reading a test frame for a few seconds
                start_time = time.time()
                while time.time() - start_time < 5:  # 5 second timeout
                    ret, frame = self.cap.read()
                    if ret and frame is not None and frame.size > 0:
                        logging.info(f"Successfully connected to camera using URL: {url}")
                        return True
                    time.sleep(0.1)
                
                logging.warning(f"Unable to retrieve a test frame from URL: {url}")
                self.cap.release()
                
            except Exception as e:
                logging.warning(f"Error connecting using URL {url}: {str(e)}")
                if self.cap:
                    self.cap.release()
                continue
        
        logging.error("Failed to connect using any available RTSP URL format")
        return False
    
    def capture_frame(self):
        """
        Capture a single frame from the camera and save it to the output directory.
        
        Returns:
            tuple: (bool, str) - Success status and path to saved image if successful
        """
        if self.cap is None or not self.cap.isOpened():
            logging.error("Camera connection not established")
            return False, None
        
        # Try to read a frame with timeout
        start_time = time.time()
        while time.time() - start_time < 3:  # 3 second timeout
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                break
            time.sleep(0.1)
        
        if not ret or frame is None or frame.size == 0:
            logging.error("Failed to capture valid frame")
            return False, None
        
        # Generate a filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"frame_{timestamp}.jpg")
        
        # Save the frame to a file
        cv2.imwrite(filename, frame)
        logging.info(f"Captured frame saved to {filename}")
        return True, filename
    
    def encode_image_to_base64(self, image_path):
        """Convert image to base64 string."""
        img = Image.open(image_path)
        
        # Resize image if too large (max 4MB)
        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def analyze_image(self, image_path):
        """
        Analyze an image using Gemini Flash 2.0 API.
        
        Args:
            image_path (str): Path to the image to analyze
            
        Returns:
            dict: Analysis results with timestamp and analysis text
        """
        try:
            # Convert image to base64
            image_base64 = self.encode_image_to_base64(image_path)
            
            # Create the request payload
            payload = {
                "contents": [{
                    "parts":[{
                        "text": """Analyze this surveillance image and identify any notable activities, people, or objects.
                        Look for:
                        1. Number of people present
                        2. What activities people are engaged in
                        3. Any unusual or suspicious behavior
                        4. Key objects in the scene
                        5. General description of the environment
                        
                        Provide a detailed analysis of what you observe in this surveillance footage."""
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
                analysis_text = f"Error analyzing image: {response.status_code} - {response.text}"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return {
                'timestamp': timestamp,
                'image_path': image_path,
                'analysis': analysis_text
            }
            
        except Exception as e:
            logging.error(f"Error analyzing image: {str(e)}")
            return {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_path': image_path,
                'analysis': f"Error: {str(e)}"
            }
    
    async def send_to_telegram(self, analysis_result):
        """
        Send the analysis and image to Telegram.
        
        Args:
            analysis_result (dict): Analysis result containing timestamp, image path, and analysis text
        """
        try:
            # Format message
            message = (
                f"🔍 <b>Surveillance Analysis</b>\n\n"
                f"⏱️ <b>Timestamp:</b> {analysis_result['timestamp']}\n\n"
                f"📝 <b>Analysis:</b>\n{analysis_result['analysis']}"
            )
            
            # Send message
            await self.telegram.send_message(message)
            
            # Send image
            await self.telegram.bot.send_photo(
                chat_id=self.telegram.chat_id,
                photo=open(analysis_result['image_path'], 'rb'),
                caption=f"Surveillance image captured at {analysis_result['timestamp']}"
            )
            
            logging.info("Analysis and image sent to Telegram successfully")
            
        except Exception as e:
            logging.error(f"Error sending to Telegram: {str(e)}")
    
    def disconnect(self):
        """Release the camera connection."""
        if self.cap:
            self.cap.release()
            logging.info("Camera disconnected")
    
    def save_analysis_results(self, analysis_result):
        """
        Save analysis results to a JSON file.
        
        Args:
            analysis_result (dict): Analysis result containing timestamp, image path, and analysis text
        """
        # Create a filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.analysis_dir, f"analysis_{timestamp}.json")
        
        # Save analysis results to a file
        with open(filename, 'w') as f:
            json.dump(analysis_result, f, indent=4)
        
        logging.info(f"Analysis results saved to {filename}")
    
    async def run_surveillance(self, interval=60, duration=None):
        """
        Run continuous surveillance at a specified interval.
        
        Args:
            interval (int): Time (in seconds) between captures.
            duration (int or None): Total duration for surveillance (seconds). None for indefinite surveillance.
        """
        if not self.connect():
            return
        
        start_time = time.time()
        try:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    logging.info("Surveillance duration reached")
                    break
                
                # Capture a frame
                success, image_path = self.capture_frame()
                if not success:
                    logging.error("Failed to capture frame, attempting to reconnect...")
                    self.disconnect()
                    if not self.connect():
                        logging.error("Failed to reconnect to camera, exiting...")
                        break
                    continue
                
                # Analyze the image
                analysis_result = self.analyze_image(image_path)
                
                # Save analysis results
                self.save_analysis_results(analysis_result)
                
                # Send to Telegram
                await self.send_to_telegram(analysis_result)
                
                # Wait for the next interval
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logging.info("Surveillance stopped by user")
        finally:
            self.disconnect()

async def main():
    # Camera configuration
    CAMERA_IP = "192.168.1.130"  # Replace with your camera's IP
    USERNAME = "admin"           # Replace with your camera's username
    PASSWORD = "admin"           # Replace with your camera's password
    
    # Initialize surveillance system
    surveillance = CameraSurveillance(
        camera_ip=CAMERA_IP,
        username=USERNAME,
        password=PASSWORD
    )
    
    # Start surveillance (captures and analyzes a frame every 60 seconds)
    await surveillance.run_surveillance(interval=60)

if __name__ == "__main__":
    asyncio.run(main())