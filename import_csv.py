import pandas as pd
import sqlite3
import os

# 현재 프로젝트 루트 경로 기준으로 DB 경로 고정
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

# CSV 읽기
df = pd.read_csv("logs.csv")

# SQLite 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# logs 테이블에 삽입
df.to_sql("log", conn, if_exists="append", index=False)

# 삽입 후 총 데이터 개수 확인
cursor.execute("SELECT COUNT(*) FROM log;")
count = cursor.fetchone()[0]

print("✅ CSV 데이터가 DB에 추가되었습니다.")
print(f"📊 현재 log 테이블 총 데이터 개수: {count} 개")

conn.close()
