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
        amount REAL NOT NULL,           -- Số dương cho thu, số âm cho chi
        category_id INTEGER NOT NULL,   -- Tham chiếu sang bảng categories
        note TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id)
        )
                    ''')
    #Tao bang categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            type INTERGER NOT NULL CHECK (type IN (0, 1)) -- 0: chi, 1: thu
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

def create_category(key, value, category_type):
    """Tạo category mới."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO categories (key, value, type)
            VALUES (?, ?, ?)
        ''', (key, value, category_type))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # Key đã tồn tại
    finally:
        conn.close()

def get_all_categories():
    """Lấy tất cả categories."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM categories ORDER BY type, value')
    rows = cursor.fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

def get_categories_by_type(category_type):
    """Lấy categories theo loại (0: chi, 1: thu)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM categories WHERE type = ? ORDER BY value', (category_type,))
    rows = cursor.fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

def update_category(key, value=None, category_type=None):
    """Cập nhật category."""
    conn = get_connection()
    cursor = conn.cursor()
    
    update_fields = []
    values = []
    
    if value is not None:
        update_fields.append('value = ?')
        values.append(value)
    if category_type is not None:
        update_fields.append('type = ?')
        values.append(category_type)
    
    if not update_fields:
        conn.close()
        return False
    
    query = f'UPDATE categories SET {", ".join(update_fields)} WHERE key = ?'
    values.append(key)
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

def delete_category(key):
    """Xóa category."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Kiểm tra xem category có đang được sử dụng không
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE category_id = (SELECT id FROM categories WHERE key = ?)', (key,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        conn.close()
        return False  # Không thể xóa vì đang được sử dụng
    
    cursor.execute('DELETE FROM categories WHERE key = ?', (key,))
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

def get_setting(key):
    """Lấy giá trị setting."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    
    conn.close()
    return row['value'] if row else None

def set_setting(key, value):
    """Thiết lập giá trị setting."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    ''', (key, value))
    
    conn.commit()
    conn.close()

def get_budget_limit():
    """Lấy hạn mức ngân sách."""
    budget_str = get_setting('budget_limit')
    return float(budget_str) if budget_str else 0.0

def set_budget_limit(amount):
    """Thiết lập hạn mức ngân sách."""
    set_setting('budget_limit', str(amount))


def backup_database(backup_path=None):
    """Sao lưu database."""
    if backup_path is None:
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'database/backup_{timestamp}.db'
    
    # Đảm bảo thư mục backup tồn tại
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    conn = get_connection()
    
    # Tạo kết nối tới file backup
    backup_conn = sqlite3.connect(backup_path)
    
    # Sao chép dữ liệu
    with backup_conn:
        conn.backup(backup_conn)
    
    conn.close()
    backup_conn.close()
    
    return backup_path

def get_database_stats():
    """Lấy thống kê database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Đếm số giao dịch
    cursor.execute('SELECT COUNT(*) FROM transactions')
    stats['total_transactions'] = cursor.fetchone()[0]
    
    # Đếm số categories
    cursor.execute('SELECT COUNT(*) FROM categories')
    stats['total_categories'] = cursor.fetchone()[0]
    
    # Tổng thu
    cursor.execute('SELECT SUM(amount) FROM transactions WHERE amount > 0')
    stats['total_income'] = cursor.fetchone()[0] or 0
    
    # Tổng chi
    cursor.execute('SELECT SUM(amount) FROM transactions WHERE amount < 0')
    stats['total_expense'] = cursor.fetchone()[0] or 0
    
    # Số dư hiện tại
    stats['current_balance'] = stats['total_income'] + stats['total_expense']
    
    conn.close()
    return stats

def reset_database():
    """Reset database về trạng thái ban đầu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Xóa tất cả dữ liệu
    cursor.execute('DELETE FROM transactions')
    cursor.execute('DELETE FROM categories')
    cursor.execute('DELETE FROM settings')
    
    # Reset auto-increment
    cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("transactions", "categories")')
    
    conn.commit()
    conn.close()
    
    # Khởi tạo lại
    init_db()

def validate_database():
    """Kiểm tra tính toàn vẹn của database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    issues = []
    
    # Kiểm tra foreign key constraints
    cursor.execute('PRAGMA foreign_key_check')
    fk_issues = cursor.fetchall()
    if fk_issues:
        issues.extend([f"Foreign key violation: {issue}" for issue in fk_issues])
    
    # Kiểm tra integrity
    cursor.execute('PRAGMA integrity_check')
    integrity_result = cursor.fetchone()
    if integrity_result and integrity_result[0] != 'ok':
        issues.append(f"Integrity check failed: {integrity_result[0]}")
    
    conn.close()
    return issues

def get_transactions_by_date_range(start_date, end_date):
    """Lấy giao dịch theo khoảng thời gian."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.*, c.value as category_name, c.type as category_type
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.date BETWEEN ? AND ?
        ORDER BY t.date DESC
    ''', (start_date, end_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_monthly_summary(year=None, month=None):
    """Lấy tổng kết theo tháng."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if year and month:
        date_pattern = f'{year:04d}-{month:02d}%'
    elif year:
        date_pattern = f'{year:04d}%'
    else:
        date_pattern = '%'
    
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_expense,
            COUNT(*) as transaction_count
        FROM transactions 
        WHERE date LIKE ?
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
    ''', (date_pattern,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_category_summary(start_date=None, end_date=None):
    """Lấy tổng kết theo category."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            c.value as category_name,
            c.type as category_type,
            SUM(t.amount) as total_amount,
            COUNT(t.id) as transaction_count
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
    '''
    
    params = []
    if start_date and end_date:
        query += ' WHERE t.date BETWEEN ? AND ?'
        params.extend([start_date, end_date])
    
    query += ' GROUP BY c.id, c.value, c.type ORDER BY ABS(SUM(t.amount)) DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def create_transaction(date, amount, category_id, note=None):
    """Tạo giao dịch mới."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (date, amount, category_id, note)
        VALUES (?, ?, ?, ?)
    ''', (date, amount, category_id, note))
    
    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()
    
    return transaction_id

def get_all_transactions():
    """Lấy tất cả giao dịch."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.*, c.value as category_name, c.type as category_type
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.date DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_transaction(transaction_id, date=None, amount=None, category_id=None, note=None):
    """Cập nhật giao dịch."""
    conn = get_connection()
    cursor = conn.cursor()
    
    update_fields = []
    values = []
    
    if date is not None:
        update_fields.append('date = ?')
        values.append(date)
    if amount is not None:
        update_fields.append('amount = ?')
        values.append(amount)
    if category_id is not None:
        update_fields.append('category_id = ?')
        values.append(category_id)
    if note is not None:
        update_fields.append('note = ?')
        values.append(note)
    
    if not update_fields:
        conn.close()
        return False
    
    query = f'UPDATE transactions SET {", ".join(update_fields)} WHERE id = ?'
    values.append(transaction_id)
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

def delete_transaction(transaction_id):
    """Xóa giao dịch."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

if __name__ == "__main__":
    init_db()