from flask import Flask, request, abort
import matplotlib.pyplot as plt
import io
import os
import requests
from datetime import datetime
import logging
import re

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

        # Extract metrics using robust pattern matching
        period = "1 hour"  # Default value
        period_match = re.search(r'Daily Report \((\d+) hours?\)', clean_text)
        if period_match:
            period = f"{period_match.group(1)} hour{'s' if int(period_match.group(1)) > 1 else ''}"

        metrics = {
            'period': period,
            'winning_trades': int(re.search(r'Winning Trades:\s*(\d+)', clean_text).group(1)),
            'losing_trades': int(re.search(r'Losing Trades:\s*(\d+)', clean_text).group(1)),
            'total_trades': int(re.search(r'Total Trades:\s*(\d+)', clean_text).group(1)),
            'win_rate': float(re.search(r'Win Rate:\s*([\d.]+)%', clean_text).group(1)),
            'net_profit': float(re.search(r'Net Profit:\s*(-?\$?[\d,.]+)', clean_text).group(1).replace('$', '').replace(',', ''))
        }

        # Extract trades (now looking for pips instead of dollars)
        trades = []
        trades_matches = re.finditer(
            r'Order\s*#(\d+):\s*(BUY|SELL)\s+(\w+)\s*\|\s*Profit:\s*(-?\d+)\s*pips',
            clean_text
        )
        
        for match in trades_matches:
            trades.append({
                'order_id': match.group(1),
                'type': match.group(2),
                'symbol': match.group(3),
                'profit_pips': int(match.group(4))
            })

        return {**metrics, 'trades': trades}
        
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        raise

def generate_report_image(report_data):
    """Generate clean, minimalist report image with improved English formatting"""
    try:
        # Create figure with specific dimensions
        plt.figure(figsize=(10, 8))  # Increased height for better spacing
        ax = plt.gca()
        ax.axis('off')

        # Set background color
        fig = plt.gcf()
        fig.patch.set_facecolor('#f8f9fa')  # Light gray background
        ax.set_facecolor('#f8f9fa')

        # Title with stars
        title = "****** Kin99old_copytrading Report ******"
        
        # Report content with improved formatting
        content = [
            f"📅 Reporting Period: {report_data['period']}",
            "",
            f"📊 Total Trades: {report_data['total_trades']}",
            f"✅ Winning Trades: {report_data['winning_trades']}",
            f"❌ Losing Trades: {report_data['losing_trades']}",
            f"🎯 Win Rate: {report_data['win_rate']:.1f}%",
            f"💰 Net Profit: {report_data['net_profit']:,.0f} pips",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📝 Trades Details:",
            ""
        ]

        # Add trades details if they exist
        if report_data['trades']:
            for trade in report_data['trades']:
                profit_sign = "+" if trade['profit_pips'] >= 0 else ""
                content.append(
                    f"#{trade['order_id']}: {trade['type']} {trade['symbol']} | "
                    f"Profit: {profit_sign}{trade['profit_pips']} pips"
                )
        else:
            content.append("No trades details available")
            
        # Add footer
        content.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"🔄 Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "📊 @Kin99old_copytrading"
        ])

        # Add title to plot
        plt.text(0.5, 0.97, title,
                fontsize=14,
                fontweight='bold',
                fontfamily='sans-serif',
                horizontalalignment='center',
                transform=ax.transAxes)

        # Add content to plot with specific styling
        plt.text(0.05, 0.85, '\n'.join(content),
                fontsize=11,
                fontfamily='sans-serif',
                verticalalignment='top',
                linespacing=1.8)

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        logger.info("Minimalist report image generated")
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
        caption = "****** Kin99old_copytrading Report ******"
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
