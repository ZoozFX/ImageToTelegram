from flask import Flask, request, abort
import matplotlib.pyplot as plt
import io
import os
import requests
from datetime import datetime
import logging
import re
import numpy as np

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7570975386:AAG2Z2myM-w6fN00T7NugvraRPT5Rj9Yjso')
CHAT_ID = os.environ.get('CHAT_ID', '-1002799925948')
SECRET_KEY = os.environ.get('SECRET_KEY', '8D81Yqh4lJbUsqGWpD9zCl1jQubexk')

def parse_html_content(html_content):
    """Extract data from HTML content with improved parsing"""
    try:
        # Remove HTML tags and clean content
        clean_text = re.sub('<[^<]+?>', '', html_content)
        clean_text = ' '.join(clean_text.split())
        
        # Debug log
        logger.info(f"Cleaned content: {clean_text[:200]}...")

        # Extract metrics
        period = "1 hour"  # Default value
        period_match = re.search(r'Daily Report \((\d+) hours?\)', clean_text)
        if period_match:
            period = f"{period_match.group(1)} hours"

        # Initialize variables for pips calculation
        total_pips = 0.0
        trades = []
        
        # Extract trades and convert profit to pips
        trades_matches = re.finditer(
            r'Order\s*#(\d+):\s*(BUY|SELL)\s+(\w+)\s*\|\s*Profit:\s*(-?[\d.]+)\s*pips',
            clean_text
        )
        
        for match in trades_matches:
            pips = float(match.group(4))
            total_pips += pips
            trades.append({
                'order_id': match.group(1),
                'type': match.group(2),
                'symbol': match.group(3),
                'profit_pips': pips
            })

        # Extract win/loss counts
        winning_trades = int(re.search(r'Winning Trades:\s*(\d+)', clean_text).group(1))
        losing_trades = int(re.search(r'Losing Trades:\s*(\d+)', clean_text).group(1))
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Extract net profit (handle both integer and decimal values)
        net_profit_match = re.search(r'Net Profit:\s*(-?[\d.]+)\s*pips', clean_text)
        if net_profit_match:
            total_pips = float(net_profit_match.group(1))

        logger.info("Parsed data: {\n" +
                   f"  'period': '{period}',\n" +
                   f"  'winning_trades': {winning_trades},\n" +
                   f"  'losing_trades': {losing_trades},\n" +
                   f"  'total_trades': {total_trades},\n" +
                   f"  'win_rate': {win_rate},\n" +
                   f"  'net_pips': {total_pips},\n" +
                   f"  'trades_count': {len(trades)}\n" +
                   "}")

        return {
            'period': period,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'net_pips': total_pips,
            'trades': trades
        }
        
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        raise

def generate_report_image(report_data):
    """Generate professional report image without trades details"""
    try:
        # Create figure with adjusted dimensions
        plt.figure(figsize=(12, 8))  # Reduced height since we removed trades details
        ax = plt.gca()
        ax.axis('off')

        # Custom color scheme
        bg_color = '#1a1a2e'  # Dark blue background
        text_color = '#e6e6e6'  # Light gray text
        accent_color = '#4cc9f0'  # Bright blue for accents
        divider_color = '#4a4e69'  # Medium gray for dividers

        # Set background color
        fig = plt.gcf()
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)

        # Title with custom styling
        title = "Kin99old_copytrading Report"
        plt.text(0.5, 0.95, title,
                fontsize=24,
                fontweight='bold',
                color=accent_color,
                fontfamily='sans-serif',
                horizontalalignment='center',
                transform=ax.transAxes)

        # Watermark
        watermark_text = "@Kin9support"
        plt.text(0.5, 0.5, watermark_text,
                fontsize=120,
                color='#ffffff10',  # Very transparent white
                fontweight='bold',
                fontfamily='sans-serif',
                horizontalalignment='center',
                verticalalignment='center',
                rotation=30,
                transform=ax.transAxes)

        # Report content (without trades details)
        content = [
            f"Reporting Period: {report_data['period']}",
            "",
            f"Total Trades: {report_data['total_trades']}",
            f"Winning Trades: {report_data['winning_trades']}",
            f"Losing Trades: {report_data['losing_trades']}",
            f"Win Rate: {report_data['win_rate']:.1f}%",
            f"Net Profit: {report_data['net_pips']:+,.1f} pips",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "© Kin99old_copytrading Report"
        ]

        # Add content to plot (adjusted vertical position)
        plt.text(0.1, 0.85, '\n'.join(content),
                fontsize=16,
                color=text_color,
                fontfamily='sans-serif',
                verticalalignment='top',
                linespacing=1.8)

        # Highlight important metrics (adjusted positions)
        important_metrics = [
            (0.8, 0.75, f"Net Profit: {report_data['net_pips']:+,.1f} pips", 20),
            (0.8, 0.7, f"Win Rate: {report_data['win_rate']:.1f}%", 20)
        ]
        
        for x, y, text, size in important_metrics:
            plt.text(x, y, text,
                    fontsize=size,
                    fontweight='bold',
                    color=accent_color,
                    fontfamily='sans-serif',
                    horizontalalignment='center',
                    transform=ax.transAxes)

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        logger.info("Professional report image generated (without trades details)")
        return buf

    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Authentication
        if request.headers.get('X-Secret-Key') != SECRET_KEY:
            logger.warning("Unauthorized access attempt")
            abort(401)

        if 'file' not in request.files:
            logger.error("No file part in request")
            return "No file uploaded", 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("Empty filename received")
            return "No file selected", 400

        # Process file
        content = file.read().decode('utf-8')
        report_data = parse_html_content(content)
        
        # Generate and send image
        img_buffer = generate_report_image(report_data)
        caption = "https://t.me/Kin99old/768"
        send_telegram_photo(img_buffer, caption)
        
        return "✅ Report sent successfully", 200

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        send_telegram_message(f"⚠️ Report Error: {str(e)}")
        return f"❌ Error: {str(e)}", 500

def send_telegram_photo(image_buffer, caption=""):
    """Send photo to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': ('report.png', image_buffer.getvalue(), 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        
        response = requests.post(url, files=files, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except Exception as e:
        logger.error(f"Telegram send error: {str(e)}")
        raise

def send_telegram_message(text):
    """Send text message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
