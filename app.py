from flask import Flask, request, abort
import matplotlib.pyplot as plt
from matplotlib import font_manager
import io
import os
import requests
from datetime import datetime
import logging
import html

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7570975386:AAG2Z2myM-w6fN00T7NugvraRPT5Rj9Yjso')
CHAT_ID = os.environ.get('CHAT_ID', '-1002799925948')
SECRET_KEY = os.environ.get('SECRET_KEY', '8D81Yqh4lJbUsqGWpD9zCl1jQubexk')

# Load better font
try:
    font_path = os.path.join(os.path.dirname(__file__), 'arial.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
except:
    plt.rcParams['font.family'] = 'DejaVu Sans'  # Fallback font

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Authentication check
        if request.headers.get('X-Secret-Key') != SECRET_KEY:
            logger.warning("Unauthorized access attempt")
            abort(401, description="Invalid Secret Key")

        if 'file' not in request.files:
            logger.error("No file part in request")
            return "No file uploaded", 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("Empty filename received")
            return "No file selected", 400

        content = file.read().decode('utf-8')
        logger.info(f"Processing file with {len(content)} characters")

        # Extract relevant data from HTML
        report_data = parse_html_content(content)
        
        # Generate high-quality report image
        img_buffer = generate_report_image(report_data)
        
        # Send to Telegram
        caption = f"📊 Daily Trading Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        telegram_response = send_telegram_photo(img_buffer, caption)
        
        logger.info(f"Telegram API response: {telegram_response}")
        return "✅ Report successfully sent to Telegram", 200

    except Exception as e:
        error_msg = f"❌ Server Error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        send_telegram_message(error_msg)
        return error_msg, 500

def parse_html_content(html_content):
    """Extract and clean report data from HTML"""
    try:
        # Remove HTML tags and decode entities
        clean_text = html.unescape(html_content)
        clean_text = ' '.join(clean_text.split()).replace('<', ' <').replace('>', '> ')
        
        # Extract key metrics
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        report_data = {
            'period': '24 hours',  # Default
            'winning_trades': 0,
            'losing_trades': 0,
            'total_trades': 0,
            'win_rate': 0.0,
            'net_profit': 0.0,
            'trades': []
        }
        
        for line in lines:
            if 'Daily Report (' in line:
                report_data['period'] = line.split('(')[1].split(')')[0]
            elif 'Winning Trades:' in line:
                report_data['winning_trades'] = int(line.split(':')[1].strip())
            elif 'Losing Trades:' in line:
                report_data['losing_trades'] = int(line.split(':')[1].strip())
            elif 'Total Trades:' in line:
                report_data['total_trades'] = int(line.split(':')[1].strip())
            elif 'Win Rate:' in line:
                report_data['win_rate'] = float(line.split(':')[1].replace('%', '').strip())
            elif 'Net Profit:' in line:
                report_data['net_profit'] = float(line.split('$')[0].split(':')[1].strip())
            elif 'Order #' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    trade = {
                        'order_id': parts[0].split('#')[1].split(':')[0].strip(),
                        'type': parts[0].split(':')[1].strip().split()[0],
                        'symbol': parts[0].split(':')[1].strip().split()[1],
                        'profit': float(parts[1].split(':')[1].strip())
                    }
                    report_data['trades'].append(trade)
        
        return report_data
    
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        raise

def generate_report_image(report_data):
    """Generate professional trading report image"""
    try:
        # Create figure with custom styling
        fig, ax = plt.subplots(figsize=(14, 10))
        fig.patch.set_facecolor('#f5f7fa')
        ax.set_facecolor('#ffffff')
        ax.axis('off')
        
        # Title
        plt.suptitle('DAILY TRADING REPORT', 
                    fontsize=18, 
                    fontweight='bold',
                    color='#2c3e50',
                    y=0.98)
        
        # Summary section
        summary_text = (
            f"Reporting Period: {report_data['period']}\n"
            f"Total Trades: {report_data['total_trades']}\n"
            f"Winning Trades: {report_data['winning_trades']} | "
            f"Losing Trades: {report_data['losing_trades']}\n"
            f"Win Rate: {report_data['win_rate']:.1f}%\n"
            f"Net Profit: ${report_data['net_profit']:,.2f}"
        )
        
        plt.text(0.05, 0.85, summary_text,
                fontsize=14,
                linespacing=1.8,
                bbox=dict(facecolor='#e8f4fc',
                          edgecolor='#3498db',
                          boxstyle='round,pad=1'))
        
        # Trades details
        if report_data['trades']:
            trades_text = "\nTRADES DETAILS:\n" + "\n".join(
                f"{trade['order_id']}: {trade['type']} {trade['symbol']} | "
                f"Profit: ${trade['profit']:,.2f}"
                for trade in report_data['trades']
            )
            
            plt.text(0.05, 0.5, trades_text,
                    fontsize=12,
                    fontfamily='monospace',
                    linespacing=1.6,
                    bbox=dict(facecolor='#ffffff',
                              edgecolor='#e0e0e0',
                              boxstyle='round,pad=1'))
        
        # Footer
        plt.text(0.5, 0.02, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                fontsize=10,
                color='#7f8c8d',
                ha='center')
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', 
                   dpi=120,
                   bbox_inches='tight',
                   facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close()
        
        logger.info("Professional report image generated")
        return buf

    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise

def send_telegram_photo(image_buffer, caption=""):
    """Send photo to Telegram with error handling"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        
        files = {'photo': ('daily_report.png', image_buffer.getvalue(), 'image/png')}
        data = {
            'chat_id': CHAT_ID,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, files=files, data=data, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API Error: {str(e)}")
        return send_as_document(image_buffer, caption)
    
    except Exception as e:
        logger.error(f"Unexpected Telegram error: {str(e)}")
        raise

def send_as_document(image_buffer, caption):
    """Fallback method to send as document"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        files = {'document': ('daily_report.png', image_buffer.getvalue(), 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    except Exception as e:
        error_msg = f"Failed to send document: {str(e)}"
        logger.error(error_msg)
        send_telegram_message("⚠️ Failed to send report. " + error_msg)
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
