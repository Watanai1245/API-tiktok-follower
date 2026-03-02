from flask import Flask
from api.followers import followers_route
from api.video import video_route

app = Flask(__name__)

app.add_url_rule("/api/followers", view_func=followers_route)
app.add_url_rule("/api/video", view_func=video_route)

@app.get("/")
def home():
    return {"status": "API running"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)