import cohere
import json

with open("credentions.json", encoding="utf-8") as f:
    secrets = json.load(f)
api_key = secrets["COHERE_API_KEY"]

co = cohere.ClientV2(api_key) 

# Потоковая обработка ответа
res = co.chat_stream(
    model="command-a-03-2025",
    messages=[
        {
            "role": "user",
            "content": "На каких языках ты умеешь общаться?",
        }
    ],
)
for chunk in res:
    if chunk:
        if chunk.type == "content-delta":
            print(chunk.delta.message.content.text, end="")