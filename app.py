from flask import Flask, request
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests

app = Flask(__name__)
TELEGRAM_TOKEN = "your-telegram-token"
CHAT_ID = "your-chat-id"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400
    
    # حفظ الملف مؤقتاً
    filepath = os.path.join('uploads', file.filename)
    file.save(filepath)
    
    # قراءة المحتوى
    with open(filepath, 'r') as f:
        content = f.read()
    
    # تحويل إلى صورة
    img = generate_report_image(content)
    
    # إرسال إلى تليجرام
    send_telegram_photo(img)
    
    # تنظيف الملف المؤقت
    os.remove(filepath)
    
    return "Report processed", 200

def generate_report_image(text):
    # إنشاء صورة باستخدام matplotlib
    plt.figure(figsize=(10, 6))
    plt.axis('off')
    plt.text(0.1, 0.5, text, fontsize=10, family='monospace')
    
    # حفظ الصورة في buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plt.close()
    
    return buf

def send_telegram_photo(image_buffer):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': ('report.png', image_buffer, 'image/png')}
    data = {'chat_id': CHAT_ID}
    
    response = requests.post(url, files=files, data=data)
    return response.json()

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
