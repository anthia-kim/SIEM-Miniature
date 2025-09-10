import pandas as pd
import sqlite3

# CSV 읽기
df = pd.read_csv("logs.csv")

# SQLite 연결
conn = sqlite3.connect("database.db")

# logs 테이블에 삽입
df.to_sql("log", conn, if_exists="append", index=False)

print("✅ CSV 데이터가 DB에 추가되었습니다.")
