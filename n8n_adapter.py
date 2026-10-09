import os
import json
import requests
import subprocess
import base64
from vieneu import Vieneu

# 1. NHẬN DỮ LIỆU TỪ n8n
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
data = json.loads(payload_str)

text = data.get('text', 'Xin chào, đây là hệ thống thử nghiệm.')
voice_name = data.get('voice', 'Hải Đăng')
speed_val = data.get('speed', 1.0)
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token')

# DÁN LINK GOOGLE APPS SCRIPT MỚI CỦA BẠN VÀO ĐÂY:
gas_url = "THAY_BẰNG_LINK_WEB_APP_URL_CỦA_BẠN"

headers = {}
if webhook_token:
    headers['x-webhook-token'] = webhook_token

print(f"Bắt đầu tạo giọng '{voice_name}' (Tốc độ: {speed_val}) cho văn bản: {text}")

# 2. KHỞI CHẠY AI VÀ TẠO ÂM THANH
try:
    tts_engine = Vieneu()
    audio = tts_engine.infer(text, voice=voice_name, speed=speed_val)
    
    tts_engine.save(audio, "result.wav")
    print("Tạo file WAV gốc thành công!")
    
    print("Đang nén sang định dạng MP3...")
    subprocess.run("ffmpeg -i result.wav -b:a 128k result.mp3 -y", shell=True, check=True)
    print("Nén MP3 thành công!")
    
except Exception as e:
    print(f"Lỗi hệ thống/AI: {e}")
    if webhook_url:
        requests.post(webhook_url, json={"status": "error", "message": f"Lỗi quá trình xử lý: {str(e)}"}, headers=headers)
    exit(1)

# 3. MÃ HÓA VÀ GỬI FILE LÊN GOOGLE DRIVE
if os.path.exists("result.mp3"):
    print("Đang mã hóa dữ liệu và tải lên Google Drive...")
    try:
        # Đọc file MP3 và biến thành chuỗi văn bản Base64
        with open("result.mp3", "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')
            
        json_payload = {
            'filename': 'audio_result.mp3',
            'mimeType': 'audio/mpeg',
            'fileData': encoded_string
        }
        
        # Gửi gói văn bản JSON chứa file cho Google
        response = requests.post(gas_url, json=json_payload, timeout=120)
        
        try:
            result_json = response.json()
        except Exception:
            result_json = {"status": "error", "message": "Google trả về dữ liệu không hợp lệ"}

        if result_json.get("status") == "success":
            print(f"Tải lên Drive thành công! Link file: {result_json.get('fileUrl')}")
            
            if webhook_url:
                requests.post(webhook_url, json={"status": "success", "drive_link": result_json.get('fileUrl')}, headers=headers)
                print("Đã báo cáo link thành công về n8n!")
        else:
            print(f"Google Apps Script báo lỗi: {result_json.get('message')}")
            if webhook_url:
                requests.post(webhook_url, json={"status": "error", "message": f"Lỗi tải lên Drive: {result_json.get('message')}"}, headers=headers)
                
    except Exception as e:
        print(f"Lỗi kết nối tải lên Drive: {e}")
        if webhook_url:
            requests.post(webhook_url, json={"status": "error", "message": str(e)}, headers=headers)
