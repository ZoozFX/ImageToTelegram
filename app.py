from flask import Flask, request, abort
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
from datetime import datetime

app = Flask(__name__)

# 1. إعدادات يجب تغييرها (ضعها كمتغيرات بيئة في Render)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7570975386:AAG2Z2myM-w6fN00T7NugvraRPT5Rj9Yjso')  # استبدل ببوتك
CHAT_ID = os.environ.get('CHAT_ID', '-1002799925948')  # استبدل بآيدي شاتك
SECRET_KEY = os.environ.get('SECRET_KEY', '8D81Yqh4lJbUsqGWpD9zCl1jQubexk')  # استخدم نفس السكرت كي في EA

@app.route('/upload', methods=['POST'])
def upload_file():
    # 2. التحقق من السكرت كي
    if request.headers.get('X-Secret-Key') != SECRET_KEY:
        abort(401, description="Unauthorized: Invalid Secret Key")

    # 3. معالجة الملف
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    try:
        # قراءة المحتوى مباشرة بدون حفظ ملف
        content = file.read().decode('utf-8')
        
        # 4. تحسين توليد الصورة
        img = generate_report_image(content)
        
        # 5. إرسال الصورة مع تعليق
        send_telegram_photo(img, f"📊 Report {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "✅ Report sent to Telegram", 200
    
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        send_telegram_message(error_msg)  # إرسال الخطأ إلى التليجرام
        return error_msg, 500

def generate_report_image(text):
    # 6. تصميم صورة أفضل
    plt.figure(figsize=(12, 8), facecolor='#f5f5f5')
    plt.axis('off')
    plt.title('Daily Trading Report', fontsize=14, pad=20, color='#2c3e50')
    
    # إضافة شبكة خلفية
    plt.gca().set_facecolor('#ffffff')
    
    # تحسين عرض النص
    plt.text(0.05, 0.5, text, 
             fontfamily='monospace',
             fontsize=10,
             linespacing=1.5,
             bbox=dict(facecolor='white', alpha=0.8, pad=10))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def send_telegram_photo(image_buffer, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': ('report.png', image_buffer, 'image/png')}
    data = {'chat_id': CHAT_ID, 'caption': caption}
    
    response = requests.post(url, files=files, data=data)
    if response.status_code != 200:
        raise Exception(f"Telegram API Error: {response.text}")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    requests.post(url, data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
