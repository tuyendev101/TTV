import os
import json
import requests
import subprocess
from vieneu import Vieneu

# 1. NHẬN DỮ LIỆU TỪ N8N (ẨN DANH TRONG LOG GITHUB)
payload_str = os.environ.get('PAYLOAD_DATA', '{}')
try:
    data = json.loads(payload_str)
except:
    data = {}

text = data.get('text', 'Xin chào')
voice_name = data.get('voice', 'Hải Đăng')
speed_val = data.get('speed', 1.0)
webhook_url = data.get('n8n_webhook')
webhook_token = data.get('webhook_token')
file_name = data.get('file_name', 'audio_result.mp3')

# Thông tin xác thực Google Drive
client_id = data.get('client_id')
client_secret = data.get('client_secret')
refresh_token = data.get('refresh_token')
folder_id = data.get('folder_id')

headers = {}
if webhook_token:
    headers['x-webhook-token'] = webhook_token

def report_to_n8n(status, message, drive_link=None):
    if not webhook_url:
        return
    payload = {"status": status, "message": message}
    if drive_link:
        payload["drive_link"] = drive_link
    try:
        requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    except:
        pass

print(f"Bắt đầu tạo giọng '{voice_name}' (Tốc độ: {speed_val})")

# 2. KHỞI CHẠY AI & NÉN
try:
    tts_engine = Vieneu()
    audio = tts_engine.infer(text, voice=voice_name, speed=speed_val)
    tts_engine.save(audio, "result.wav")
    print("Tạo âm thanh AI thành công.")
    
    # Nén 64k mono cực nhẹ, loglevel error để giấu chi tiết nén
    subprocess.run("ffmpeg -i result.wav -b:a 64k -ac 1 result.mp3 -y -loglevel error", shell=True, check=True)
    print("Nén file MP3 hoàn tất.")
except Exception as e:
    print("Lỗi trong quá trình tạo âm thanh hoặc nén file.")
    report_to_n8n("error", f"Lỗi TTS: {str(e)}")
    exit(1)

# 3. UPLOAD LÊN GOOGLE DRIVE (API CHÍNH THỨC)
if not all([client_id, client_secret, refresh_token, folder_id]):
    print("Lỗi: Thiếu thông tin Google Drive API từ đầu vào.")
    report_to_n8n("error", "Thiếu Client ID, Secret, Refresh Token hoặc Folder ID.")
    exit(1)

print("Đang khởi tạo kết nối tải trực tiếp lên Google Drive...")
try:
    # A. Đổi Refresh Token lấy Access Token dùng 1 lần
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
    )
    token_data = token_response.json()
    if "access_token" not in token_data:
        raise Exception(f"Không lấy được Access Token (Kiểm tra lại Credentials).")
    
    access_token = token_data["access_token"]
    
    # B. Upload file thông qua cơ chế Multipart của Google
    metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    files = {
        'metadata': (None, json.dumps(metadata), 'application/json'),
        'file': (file_name, open("result.mp3", "rb"), 'audio/mpeg')
    }
    
    upload_response = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files
    )
    upload_data = upload_response.json()
    
    if "webViewLink" in upload_data:
        print("Đẩy file lên Google Drive thành công tuyệt đối!")
        report_to_n8n("success", "Upload hoàn tất", drive_link=upload_data["webViewLink"])
    else:
        raise Exception(f"Google Drive từ chối upload: {upload_data}")

except Exception as e:
    # Ẩn lỗi khỏi console GitHub để chống rò rỉ mã token
    print("Gặp lỗi mạng hoặc xác thực trong quá trình tải lên. Chi tiết lỗi đã gửi về n8n.")
    report_to_n8n("error", f"Lỗi Upload Drive: {str(e)}")
    exit(1)
