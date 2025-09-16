import sqlite3
import os

# 파일 경로
main_db = "database.db"            # 루트 DB
other_db = os.path.join("instance", "database.db")  # instance DB

# 루트 DB 연결
conn_main = sqlite3.connect(main_db)
cursor_main = conn_main.cursor()

# instance DB 연결
conn_other = sqlite3.connect(other_db)
cursor_other = conn_other.cursor()

# instance DB 로그 가져오기
cursor_other.execute("SELECT timestamp, ip, event_type, status FROM log")
rows = cursor_other.fetchall()

print(f"📥 instance DB에서 가져온 데이터 개수: {len(rows)} 개")

# 루트 DB에 삽입
cursor_main.executemany(
    "INSERT INTO log (timestamp, ip, event_type, status) VALUES (?, ?, ?, ?)",
    rows
)
conn_main.commit()

# 통합 후 총 데이터 개수 확인
cursor_main.execute("SELECT COUNT(*) FROM log;")
total_count = cursor_main.fetchone()[0]

print(f"✅ 두 DB를 합쳤습니다. 현재 log 테이블 전체 데이터 개수: {total_count} 개")

# 연결 종료
conn_other.close()
conn_main.close()
