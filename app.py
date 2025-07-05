from flask import Flask, request, abort
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
from datetime import datetime
import logging

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration (set these in Render.com environment variables)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7570975386:AAG2Z2myM-w6fN00T7NugvraRPT5Rj9Yjso')
CHAT_ID = os.environ.get('CHAT_ID', '-1002799925948')
SECRET_KEY = os.environ.get('SECRET_KEY', '8D81Yqh4lJbUsqGWpD9zCl1jQubexk')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # 1. Authentication check
        if request.headers.get('X-Secret-Key') != SECRET_KEY:
            logger.warning("Unauthorized access attempt")
            abort(401, description="Invalid Secret Key")

        # 2. File validation
        if 'file' not in request.files:
            logger.error("No file part in request")
            return "No file uploaded", 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("Empty filename received")
            return "No file selected", 400

        # 3. Process file content
        content = file.read().decode('utf-8')
        logger.info(f"Processing file with {len(content)} characters")

        # 4. Generate report image
        img_buffer = generate_report_image(content)
        
        # 5. Send to Telegram
        caption = f"📊 Trading Report {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        telegram_response = send_telegram_photo(img_buffer, caption)
        
        logger.info(f"Telegram API response: {telegram_response}")
        return "✅ Report successfully sent to Telegram", 200

    except Exception as e:
        error_msg = f"❌ Server Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        send_telegram_message(error_msg)  # Notify admin about the error
        return error_msg, 500

def generate_report_image(text):
    """Generate professional trading report image"""
    try:
        # Create figure with custom styling
        plt.figure(figsize=(14, 8), facecolor='#f0f2f5')
        plt.axis('off')
        
        # Add title
        plt.title('DAILY TRADING REPORT', 
                 fontsize=16, pad=20, 
                 color='#2c3e50',
                 fontweight='bold')

        # Add content with improved formatting
        plt.text(0.05, 0.5, text, 
                fontfamily='DejaVu Sans Mono',
                fontsize=11,
                linespacing=1.8,
                bbox=dict(facecolor='white', 
                          edgecolor='#3498db',
                          boxstyle='round,pad=1'))

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', 
                   dpi=100,  # Optimized DPI
                   bbox_inches='tight',
                   facecolor=plt.gcf().get_facecolor())
        buf.seek(0)
        plt.close()
        
        logger.info("Image generated successfully")
        return buf

    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise

def send_telegram_photo(image_buffer, caption=""):
    """Send photo to Telegram with error handling"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        
        # Prepare file and data
        files = {'photo': ('trading_report.png', image_buffer.getvalue(), 'image/png')}
        data = {
            'chat_id': CHAT_ID,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        # Send request with timeout
        response = requests.post(url, files=files, data=data, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API Error: {str(e)}")
        # Try sending as document if photo fails
        return send_as_document(image_buffer, caption)
    
    except Exception as e:
        logger.error(f"Unexpected Telegram error: {str(e)}")
        raise

def send_as_document(image_buffer, caption):
    """Fallback method to send as document"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        files = {'document': ('report.png', image_buffer.getvalue(), 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    except Exception as e:
        error_msg = f"Failed to send document: {str(e)}"
        logger.error(error_msg)
        send_telegram_message("⚠️ Failed to send image. " + error_msg)
        raise

def send_telegram_message(text):
    """Send text message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")

if __name__ == '__main__':
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
