# Camera Surveillance with Gemini AI Analysis

This project combines IP camera surveillance with AI-powered image analysis and Telegram notifications.

## Features

- Connect to IP cameras via RTSP streams
- Capture frames at regular intervals
- Analyze images using Google's Gemini 2.0 Flash API
- Send analysis and images to Telegram for remote monitoring
- Store analysis results and images locally

## Requirements

- Python 3.8+
- OpenCV
- Google Gemini API key
- Telegram Bot token and chat ID

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TELEGRAM_CHAT_ID=your_telegram_chat_id_here
   ```

## Configuration

Modify `camera_surveillance.py` to set your camera details:

```python
def main():
    # Camera configuration
    CAMERA_IP = "192.168.1.130"  # Camera IP address
    USERNAME = "admin"           # Camera username
    PASSWORD = "admin"           # Camera password
    
    # Initialize surveillance system
    surveillance = CameraSurveillance(
        camera_ip=CAMERA_IP,
        username=USERNAME,
        password=PASSWORD
    )
```

## Usage

Run the surveillance system:

```
python camera_surveillance.py
```

This will:
1. Connect to your camera
2. Capture a frame every 60 seconds
3. Analyze the frame using Gemini AI
4. Save the frame and analysis results
5. Send the analysis and image to your Telegram

### Testing with Local Images

If your camera is offline or you want to test the analysis and Telegram features, you can use a local image:

```
python camera_surveillance.py --test-image /path/to/your/image.jpg
```

This will:
1. Process the specified image
2. Analyze it using Gemini AI
3. Send the analysis and image to your Telegram

## Telegram Setup

1. Create a Telegram bot using BotFather
2. Get your bot token
3. Get your chat ID (you can use @userinfobot)
4. Add these to your `.env` file

## Files

- `camera_surveillance.py`: Main surveillance script
- `telegram_notifier.py`: Handles Telegram notifications
- `requirements.txt`: Python dependencies
- `.env`: Environment variables for API keys and tokens