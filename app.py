import requests
from flask import Flask, request, jsonify, render_template
from models import db, Log
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
from sklearn.ensemble import IsolationForest


# .env 파일 로드
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


app = Flask(__name__)


# SQLite DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
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

    # 조건: 로그인 실패 5회 이상이면 알림
    fail_count = Log.query.filter_by(ip=data.get('ip'), event_type="login_failed").count()
    if fail_count >= 5:
        send_telegram_alert(f"🚨 다중 로그인 실패 발생! IP: {data.get('ip')}")

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

    # 원본 데이터
    timestamps = [log.timestamp for log in logs]
    event_types = [log.event_type for log in logs]
    ip_addresses = [log.ip for log in logs]

    #  시간 단위를 "YYYY-MM-DD HH"로 묶어서 집계 (분 단위 X)
    normalized_times = [t[:13] for t in timestamps]

    # 이상탐지 결과
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

    # DataFrame 변환
    df = pd.DataFrame([{
        "timestamp": log.timestamp,
        "ip": log.ip,
        "event_type": log.event_type,
        "status": log.status
    } for log in logs])

    # 시간대(feature): 0=새벽, 1=오전, 2=오후, 3=저녁
    df["hour"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.hour.fillna(0)
    df["time_bin"] = pd.cut(
        df["hour"],
        bins=[0, 6, 12, 18, 24],
        labels=[0, 1, 2, 3],
        right=False
    ).astype(int)

    # IP별 통계
    feature_df = df.groupby("ip").agg(
        total_events=("event_type", "count"),
        fail_count=("status", lambda x: (x == "failed").sum()),
        success_count=("status", lambda x: (x == "success").sum()),
        admin_access=("event_type", lambda x: (x == "admin_access").sum()),
        avg_time_bin=("time_bin", "mean")
    ).reset_index()

    # 성공/실패 비율
    feature_df["fail_ratio"] = feature_df["fail_count"] / (feature_df["total_events"] + 1e-6)

    # NaN 처리
    feature_df = feature_df.fillna(0)

    # Isolation Forest 적용
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
