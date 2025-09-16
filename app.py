import requests
from flask import Flask, request, jsonify, render_template
from models import db, Log
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
from sklearn.ensemble import IsolationForest

# .env 파일 로드
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

app = Flask(__name__)

# SQLite DB 설정 (항상 루트 DB 사용)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print("Telegram alert failed:", response.text)

# DB 초기화
with app.app_context():
    db.create_all()

# 로그 수집 API
@app.route('/log', methods=['POST'])
def collect_log():
    data = request.json
    new_log = Log(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ip=data.get('ip'),
        event_type=data.get('event'),
        status=data.get('status')
    )
    db.session.add(new_log)
    db.session.commit()

    # ✅ 조건: 최근 10분 동안 같은 IP에서 login_failed 5회 이상이면 알림
    ten_minutes_ago = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    fail_count = Log.query.filter(
        Log.ip == data.get('ip'),
        Log.event_type == "login_failed",
        Log.timestamp >= ten_minutes_ago
    ).count()

    if fail_count >= 5:
        send_telegram_alert(
            f"🚨 최근 10분 동안 다중 로그인 실패 발생! IP: {data.get('ip')} (실패 {fail_count}회)"
        )

    return jsonify({"message": "Log stored successfully!"}), 201

# 로그 확인 API
@app.route('/logs', methods=['GET'])
def get_logs():
    logs = Log.query.all()
    return jsonify([{
        "id": log.id,
        "timestamp": log.timestamp,
        "ip": log.ip,
        "event_type": log.event_type,
        "status": log.status
    } for log in logs])

# 대시보드
@app.route('/dashboard')
def dashboard():
    logs = Log.query.all()

    timestamps = [log.timestamp for log in logs if log.timestamp]
    event_types = [log.event_type for log in logs if log.event_type]
    ip_addresses = [log.ip for log in logs if log.ip]

    normalized_times = [t[:13] for t in timestamps]

    anomalies = detect_anomalies()

    return render_template(
        "dashboard.html",
        timestamps=normalized_times,
        event_types=event_types,
        ip_addresses=ip_addresses,
        anomalies=anomalies
    )

# 이상행위 탐지 API
@app.route('/anomaly')
def anomaly_api():
    anomalies = detect_anomalies()
    return jsonify(anomalies)

# 이상탐지 함수
def detect_anomalies():
    logs = Log.query.all()
    if not logs:
        return []

    df = pd.DataFrame([{
        "timestamp": log.timestamp,
        "ip": log.ip,
        "event_type": log.event_type,
        "status": log.status
    } for log in logs])

    df["hour"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.hour.fillna(0)
    df["time_bin"] = pd.cut(
        df["hour"],
        bins=[0, 6, 12, 18, 24],
        labels=[0, 1, 2, 3],
        right=False
    ).astype(int)

    feature_df = df.groupby("ip").agg(
        total_events=("event_type", "count"),
        fail_count=("status", lambda x: (x == "failed").sum()),
        success_count=("status", lambda x: (x == "success").sum()),
        admin_access=("event_type", lambda x: (x == "admin_access").sum()),
        avg_time_bin=("time_bin", "mean")
    ).reset_index()

    feature_df["fail_ratio"] = feature_df["fail_count"] / (feature_df["total_events"] + 1e-6)
    feature_df = feature_df.fillna(0)

    model = IsolationForest(contamination=0.2, random_state=42)
    feature_df["anomaly"] = model.fit_predict(feature_df[[
        "total_events",
        "fail_count",
        "success_count",
        "admin_access",
        "fail_ratio",
        "avg_time_bin"
    ]])

    return feature_df.to_dict(orient="records")

# 실행
if __name__ == '__main__':
    app.run(debug=True)
