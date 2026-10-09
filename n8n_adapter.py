import os
import json
import requests
import subprocess

# 1. Nhận dữ liệu từ n8n
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
data = json.loads(payload_str)

text = data.get('text', 'Xin chào, đây là hệ thống thử nghiệm.')
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token') # Mật khẩu bảo mật n8n

# 2. Lưu văn bản ra file text (Để truyền vào công cụ TTS)
with open("input.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Bắt đầu tạo giọng nói...")

# ==========================================
# 3. CHẠY LỆNH LÕI CỦA VIENEU-TTS
# LƯU Ý: Thay thế câu lệnh bên dưới bằng lệnh chạy file Python của repo này
# Ví dụ giả định: python inference.py --text_file input.txt --output result.wav
# ==========================================
command = "python main.py --text input.txt --output result.wav"
subprocess.run(command, shell=True)

# 4. Gửi file trực tiếp về Webhook n8n
if webhook_url:
    if os.path.exists("result.wav"):
        print(f"Đang gửi thẳng file âm thanh về n8n tại: {webhook_url}")
        try:
            # Kẹp mật khẩu vào Header để vượt qua chốt chặn bảo mật của n8n
            headers = {}
            if webhook_token:
                headers['x-webhook-token'] = webhook_token

            # Gói file vào biến 'data'
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
        requests.post(webhook_url, json={"status": "error", "message": "Quá trình render TTS thất bại"}, headers=headers)
