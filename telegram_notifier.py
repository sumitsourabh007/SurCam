import os
import json
from datetime import datetime
import asyncio
from telegram import Bot
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TelegramNotifier:
    def __init__(self):
        """Initialize the Telegram notifier."""
        load_dotenv()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env file")
        
        self.bot = Bot(token=self.bot_token)
    
    async def send_message(self, message):
        """Send a message to the configured Telegram chat."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logging.info("Message sent successfully to Telegram")
        except Exception as e:
            logging.error(f"Failed to send Telegram message: {str(e)}")
    
    async def send_analysis_summary(self, json_file_path):
        """
        Read analysis results from JSON file and send a summary to Telegram.
        
        Args:
            json_file_path (str): Path to the JSON file containing analysis results
        """
        try:
            with open(json_file_path, 'r') as f:
                results = json.load(f)
            
            # Create summary message
            summary = ["📊 <b>Exam Surveillance Analysis Summary</b>\n"]
            
            suspicious_activities = []
            for entry in results:
                timestamp = entry['timestamp']
                analysis = entry['analysis'].lower()
                
                # Check for suspicious keywords
                keywords = ['suspicious', 'looking', 'phone', 'talking', 'communication', 'device', 'cheating']
                if any(keyword in analysis for keyword in keywords):
                    suspicious_activities.append(f"⚠️ At {timestamp}:\n{entry['analysis']}\n")
            
            if suspicious_activities:
                summary.append("<b>🚨 Suspicious Activities Detected:</b>\n")
                summary.extend(suspicious_activities)
            else:
                summary.append("✅ No suspicious activities detected in this session.\n")
            
            # Add analysis timestamp
            summary.append(f"\n📅 Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Send the summary
            await self.send_message("\n".join(summary))
            
        except Exception as e:
            error_msg = f"Error processing analysis results: {str(e)}"
            logging.error(error_msg)
            await self.send_message(f"❌ {error_msg}")

def send_summary(json_file_path):
    """
    Helper function to send analysis summary without dealing with async directly.
    
    Args:
        json_file_path (str): Path to the JSON file containing analysis results
    """
    notifier = TelegramNotifier()
    asyncio.run(notifier.send_analysis_summary(json_file_path))