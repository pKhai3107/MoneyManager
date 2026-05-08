from typing import List, Dict, Optional
from modulo import db_helper
from modulo.models import Transaction, Category

class FinanceManager:
    """Quản lý các hoạt động tài chính (Thu/Chi, Danh mục)."""

    def add_transaction(self, amount: float, category_id: int, note: Optional[str] = None) -> int:
        """Thêm giao dịch mới, tự động xử lý dấu âm/dương dựa trên loại danh mục."""
        categories = self.get_all_categories()
        category = next((c for c in categories if c.id == category_id), None)
        
        if not category:
            raise ValueError(f"Category với ID {category_id} không tồn tại.")
        
        # Loại 0 (chi) -> amount âm, Loại 1 (thu) -> amount dương
        final_amount = abs(amount) if category.type == 1 else -abs(amount)
        
        transaction = Transaction.create_new(final_amount, category_id, note)
        
        return db_helper.create_transaction(
            transaction.date, 
            transaction.amount, 
            transaction.category_id, 
            transaction.note
        )

    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """Lấy danh sách các giao dịch gần nhất."""
        raw_txs = db_helper.get_all_transactions()[:limit]
        return [Transaction(**tx) for tx in raw_txs]

    def get_all_categories(self) -> List[Category]:
        """Lấy danh sách tất cả các danh mục."""
        raw_cats = db_helper.get_all_categories()
        return [Category(**cat) for cat in raw_cats]

    def get_balance_summary(self) -> Dict[str, float]:
        """Lấy tổng kết thu chi và số dư hiện tại."""
        return db_helper.get_database_stats()

    def reset_data(self) -> None:
        """Khởi tạo lại toàn bộ dữ liệu."""
        db_helper.reset_database()

    def init_storage(self) -> None:
        """Khởi tạo cơ sở dữ liệu nếu chưa có."""
        db_helper.init_db()
