import pandas as pd
import sqlite3
import os
import requests
from dotenv import load_dotenv

# .env 불러오기
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print("Telegram alert failed:", response.text)

# DB 경로 고정
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

# CSV 읽기
df = pd.read_csv("logs.csv")
df = df.dropna()  # 빈 줄 제거

# SQLite 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# CSV 데이터 삽입
df.to_sql("log", conn, if_exists="append", index=False)

# 삽입 후 총 데이터 개수 확인
cursor.execute("SELECT COUNT(*) FROM log;")
count = cursor.fetchone()[0]

print("✅ CSV 데이터가 DB에 추가되었습니다.")
print(f"📊 현재 log 테이블 총 데이터 개수: {count} 개")

# ✅ 최근 10분 기준 로그인 실패 탐지
cursor.execute("""
    SELECT ip, COUNT(*) as fail_count
    FROM log
    WHERE event_type = 'login_failed'
      AND timestamp >= datetime('now', '-10 minutes')
    GROUP BY ip
    HAVING fail_count >= 5
""")
rows = cursor.fetchall()

for ip, fails in rows:
    send_telegram_alert(f"🚨 [CSV 적재 테스트] 최근 10분 동안 {ip}에서 로그인 실패 {fails}회 발생!")

conn.close()
