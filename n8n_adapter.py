import os
import json
import requests
from vieneu import Vieneu # Import trực tiếp bộ lõi AI của VieNeu

# 1. Nhận dữ liệu từ n8n
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
data = json.loads(payload_str)

text = data.get('text', 'Xin chào, đây là hệ thống thử nghiệm.')
# Bạn có thể truyền thêm biến 'voice' từ n8n, nếu không sẽ dùng mặc định là 'Hải Đăng'
voice_name = data.get('voice', 'Hải Đăng') 
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token')

headers = {}
if webhook_token:
    headers['x-webhook-token'] = webhook_token

print(f"Bắt đầu tạo giọng '{voice_name}' cho văn bản: {text}")

# 2. KHỞI CHẠY AI VÀ TẠO ÂM THANH
try:
    # Khởi tạo engine VieNeu (mặc định v3turbo sẽ tự chạy mượt trên CPU máy ảo)
    tts_engine = Vieneu()
    
    # Tiến hành đọc văn bản
    audio = tts_engine.infer(text, voice=voice_name)
    
    # Lưu ra file audio
    tts_engine.save(audio, "result.wav")
    print("Tạo âm thanh AI thành công!")
    
except Exception as e:
    print(f"Lỗi lõi AI: {e}")
    if webhook_url:
        requests.post(webhook_url, json={"status": "error", "message": f"Lỗi AI: {str(e)}"}, headers=headers)
    exit(1)

# 3. Gửi thẳng file về n8n
if webhook_url:
    if os.path.exists("result.wav"):
        print(f"Đang gửi thẳng file âm thanh về n8n tại: {webhook_url}")
        try:
            with open("result.wav", "rb") as f:
                # Gói file vào biến 'data' để n8n tự động nhận dạng file âm thanh
                files_payload = {'data': ('audio.wav', f, 'audio/wav')}
                text_payload = {'status': 'success'}
                
                response = requests.post(webhook_url, data=text_payload, files=files_payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    print("Đã gửi file WAV về n8n thành công!")
                else:
                    print(f"Lỗi gửi file: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Lỗi: {e}")
            requests.post(webhook_url, json={"status": "error", "message": str(e)}, headers=headers)
    else:
        print("Lỗi: Không tìm thấy file result.wav được tạo ra.")
        requests.post(webhook_url, json={"status": "error", "message": "Render TTS thất bại, không có file đầu ra"}, headers=headers)
