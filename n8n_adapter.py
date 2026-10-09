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

# DÁN LINK GOOGLE APPS SCRIPT CỦA BẠN VÀO ĐÂY:
gas_url = "https://script.google.com/macros/s/AKfycbys8biUiNz_a8kOVMtde0LnxtJtYUggflpa8AdikwLK2ldVrtkpV-dBwT1lT8W9t5PP/exec"

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

# 3. GỬI FILE MP3 LÊN GOOGLE DRIVE & BÁO CÁO VỀ N8N
if os.path.exists("result.mp3"):
    print("Đang tải file MP3 trực tiếp lên Google Drive...")
    try:
        with open("result.mp3", "rb") as f:
            files_payload = {'file': ('audio_result.mp3', f, 'audio/mpeg')}
            data_payload = {'filename': 'audio_result.mp3'}
            
            # Gửi file cho Google Apps Script
            response = requests.post(gas_url, data=data_payload, files=files_payload, timeout=120)
            result_json = response.json()
            
            if result_json.get("status") == "success":
                print(f"Tải lên Drive thành công! Link file: {result_json.get('fileUrl')}")
                
                # Báo cáo kết quả về n8n (chỉ gửi link Drive dạng Text, n8n không phải gánh file)
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
