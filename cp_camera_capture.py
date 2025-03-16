import cv2
import os
import time
from datetime import datetime
import logging
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("camera_capture.log"),
        logging.StreamHandler()
    ]
)

class CPCameraCapture:
    def __init__(self, camera_ip, username, password, port=554, channel=1, output_dir="captured_images"):
        """
        Initialize the CP Plus camera capture system using multiple RTSP URL formats.
        
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
        self.cap = None

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

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
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;512000|max_delay;500000"
                
                # Create VideoCapture object with FFmpeg backend
                self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                
                if self.cap is None or not self.cap.isOpened():
                    logging.warning(f"Failed to open video capture for URL: {url}")
                    continue
                    
                # Try reading a test frame for a few seconds
                start_time = time.time()
                while time.time() - start_time < 5:  # 5 second timeout
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
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
            bool: True if capture successful, False otherwise.
        """
        if self.cap is None or not self.cap.isOpened():
            logging.error("Camera connection not established")
            return False
        
        ret, frame = self.cap.read()
        if not ret:
            logging.error("Failed to capture frame")
            return False
        
        # Generate a filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"frame_{timestamp}.jpg")
        
        # Save the frame to a file
        cv2.imwrite(filename, frame)
        logging.info("Captured frame saved to %s", filename)
        return True
    
    def disconnect(self):
        """Release the camera connection."""
        if self.cap:
            self.cap.release()
            logging.info("Camera disconnected")
    
    def run_capture(self, interval=10, duration=None):
        """
        Run continuous capture at a specified interval.
        
        Args:
            interval (int): Time (in seconds) between captures.
            duration (int or None): Total duration for capture (seconds). None for indefinite capture.
        """
        if not self.connect():
            return
        
        start_time = time.time()
        try:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    logging.info("Capture duration reached")
                    break
                self.capture_frame()
                time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("Capture stopped by user")
        finally:
            self.disconnect()

def main():
    # Camera configuration (update as necessary)
    CAMERA_IP = "192.168.1.229"  # Replace with your camera's IP
    USERNAME = "admin"           # Replace with your camera's username
    PASSWORD = "admin@123"       # Replace with your camera's password
    
    # Initialize camera capture with the specified configuration
    camera = CPCameraCapture(
        camera_ip=CAMERA_IP,
        username=USERNAME,
        password=PASSWORD,
        output_dir="cp_camera_images"
    )
    
    # Start capture (captures a frame every 10 seconds)
    camera.run_capture(interval=10)

if __name__ == "__main__":
    main()