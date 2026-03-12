from modulo import db_helper
from datetime import datetime

def add_transaction(amount, category_id, note=None, date=None):
    """Thêm giao dịch mới (tự động xử lý dấu âm/dương)."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Kiểm tra loại category để gán dấu
    categories = db_helper.get_all_categories()
    category = next((c for c in categories if c['id'] == category_id), None)
    
    if not category:
        raise ValueError("Category không tồn tại.")
    
    # Loại 0 (chi) -> amount âm, Loại 1 (thu) -> amount dương
    final_amount = abs(amount) if category['type'] == 1 else -abs(amount)
    
    return db_helper.create_transaction(date, final_amount, category_id, note)

def get_recent_transactions(limit=10):
    """Lấy danh sách giao dịch mới nhất."""
    return db_helper.get_all_transactions()[:limit]

def get_balance_summary():
    """Lấy tổng kết thu chi."""
    return db_helper.get_database_stats()
