import sqlite3
import os

def get_connection():
    """Tạo kết nối tới file database."""
    # Xây dựng đường dẫn tuyệt đối tới file database
    db_dir = os.path.join(os.path.dirname(__file__), '../database')
    db_path = os.path.join(db_dir, 'finance.db')
    
    # Đảm bảo thư mục database tồn tại
    os.makedirs(db_dir, exist_ok=True)
    
    # Kết nối tới database (sẽ tạo file nếu chưa có)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo các bảng dữ liệu lần đầu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tạo bảng transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type INTEGER NOT NULL, -- 0: Chi, 1: Thu
            note TEXT
        )
    ''')
    
    # Tạo bảng settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    # Chèn thử dữ liệu mặc định cho hạn mức nếu chưa có
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('budget_limit', '5000000')")
    
    conn.commit()
    conn.close()
    print("Khởi tạo Database thành công!")

if __name__ == "__main__":
    init_db()