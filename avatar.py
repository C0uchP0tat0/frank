import requests
import base64

DID_API_KEY = "ZDkyODAxMjkyOTJAZ21haWwuY29t:ZH9UA5E0-R08KEYWtadar"
API_URL = "https://api.d-id.com/talks"

def make_avatar_video(text: str):
    headers = {
        "Authorization": f"Basic {base64.b64encode((DID_API_KEY + ':').encode()).decode()}",
        "Content-Type": "application/json"
    }

    payload = {
        "script": {
            "type": "text",
            "input": text,
            "provider": {
                "type": "microsoft",
                "voice_id": "ru-RU-SvetlanaNeural"  # ✅ русский голос
            }
        },
        "source_url": "https://create-images-results.d-id.com/DefaultPresenters/Emma_f/image.png",
        "driver_url": "bank://lively"
    }

    r = requests.post(API_URL, headers=headers, json=payload)
    print(r.json())

make_avatar_video("Здравствуйте! Я ваш HR-аватар. Давайте начнём интервью.")
