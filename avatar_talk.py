import requests
import base64
import time

DID_API_KEY = "ZDkyODAxMjkyOTJAZ21haWwuY29t:ZH9UA5E0-R08KEYWtadar"
talk_id = "tlk_K24ALaHJ56DJZikWTXt8e"

headers = {
    "Authorization": f"Basic {base64.b64encode((DID_API_KEY + ':').encode()).decode()}",
}

while True:
    r = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers)
    data = r.json()
    print(data)
    status = data.get("status")
    if status == "done":
        video_url = data["result_url"]
        print("🎬 Видео готово:", video_url)
        break
    elif status == "error":
        print("⚠️ Ошибка генерации:", data)
        break
    time.sleep(3)
