import os
import json
import requests
import subprocess
from vieneu import Vieneu

# 1. NHẬN DỮ LIỆU TỪ n8n
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
data = json.loads(payload_str)

text = data.get('text', 'Xin chào, đây là hệ thống thử nghiệm.')
voice_name = data.get('voice', 'Hải Đăng')
speed_val = data.get('speed', 1.0)
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token')

# Thiết lập Header bảo mật (x-webhook-token)
headers = {}
if webhook_token:
    headers['x-webhook-token'] = webhook_token

print(f"Bắt đầu tạo giọng '{voice_name}' (Tốc độ: {speed_val}) cho văn bản: {text}")

# 2. KHỞI CHẠY AI VÀ TẠO ÂM THANH
try:
    tts_engine = Vieneu()
    audio = tts_engine.infer(text, voice=voice_name, speed=speed_val)
    
    # Lưu ra file WAV gốc
    tts_engine.save(audio, "result.wav")
    print("Tạo file WAV gốc thành công!")
    
    # Ép máy ảo dùng ffmpeg nén sang MP3 128kbps (Giảm 10 lần dung lượng)
    print("Đang nén sang định dạng MP3...")
    subprocess.run("ffmpeg -i result.wav -b:a 128k result.mp3 -y", shell=True, check=True)
    print("Nén MP3 thành công!")
    
except Exception as e:
    print(f"Lỗi hệ thống/AI: {e}")
    if webhook_url:
        requests.post(webhook_url, json={"status": "error", "message": f"Lỗi quá trình xử lý: {str(e)}"}, headers=headers)
    exit(1)

# 3. GỬI FILE MP3 VỀ N8N
if webhook_url:
    if os.path.exists("result.mp3"):
        print(f"Đang gửi file MP3 về n8n tại: {webhook_url}")
        try:
            with open("result.mp3", "rb") as f:
                # Gói file vào biến 'data', khai báo là file MP3
                files_payload = {'data': ('audio.mp3', f, 'audio/mpeg')}
                text_payload = {'status': 'success'}
                
                # Bắn file về n8n (chờ tối đa 120 giây cho thao tác upload)
                response = requests.post(webhook_url, data=text_payload, files=files_payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    print("Tuyệt vời! Đã ném file MP3 vào n8n thành công!")
                else:
                    print(f"Lỗi từ chối của n8n: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Lỗi mạng khi gửi file: {e}")
            requests.post(webhook_url, json={"status": "error", "message": str(e)}, headers=headers)
    else:
        print("Lỗi: Không tìm thấy file result.mp3 sau khi nén.")
        requests.post(webhook_url, json={"status": "error", "message": "Nén MP3 thất bại, không có file để gửi"}, headers=headers)
