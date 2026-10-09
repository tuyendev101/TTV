import os
import json
import requests
import subprocess

# 1. Nhận dữ liệu từ n8n
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
data = json.loads(payload_str)

text = data.get('text', 'Xin chào, đây là hệ thống thử nghiệm.')
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token')

# Đưa biến headers lên khai báo ngay từ đầu để dùng chung
headers = {}
if webhook_token:
    headers['x-webhook-token'] = webhook_token

# 2. Lưu văn bản ra file text
with open("input.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Bắt đầu tạo giọng nói...")

# ==========================================
# 3. CHẠY LỆNH LÕI CỦA VIENEU-TTS
# BẠN CẦN THAY FILE main.py THÀNH TÊN FILE ĐÚNG CỦA REPO
# ==========================================
command = "python main.py --text input.txt --output result.wav"
subprocess.run(command, shell=True)

# 4. Gửi file trực tiếp về Webhook n8n
if webhook_url:
    if os.path.exists("result.wav"):
        print(f"Đang gửi thẳng file âm thanh về n8n tại: {webhook_url}")
        try:
            with open("result.wav", "rb") as f:
                files_payload = {'data': ('audio.wav', f, 'audio/wav')}
                text_payload = {'status': 'success'}
                
                response = requests.post(webhook_url, data=text_payload, files=files_payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    print("Đã gửi thành công!")
                else:
                    print(f"Lỗi gửi file: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Lỗi: {e}")
            requests.post(webhook_url, json={"status": "error", "message": str(e)}, headers=headers)
    else:
        print("Lỗi: Không tìm thấy file result.wav được tạo ra.")
        # Bây giờ lệnh gửi lỗi này đã có biến headers hợp lệ
        requests.post(webhook_url, json={"status": "error", "message": "Quá trình render TTS thất bại do không chạy được code lõi"}, headers=headers)
