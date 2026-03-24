from modulo.transaction import FinanceManager
import sys

def main_menu(manager: FinanceManager):
    print("\n=== QUẢN LÝ TÀI CHÍNH CÁ NHÂN ===")
    
    # Hiển thị số dư nhanh
    stats = manager.get_balance_summary()
    print(f"Số dư hiện tại: {stats['current_balance']:,.0f} VND")
    print(f"(Tổng Thu: {stats['total_income']:,.0f} | Tổng Chi: {abs(stats['total_expense']):,.0f})")
    
    print("-" * 30)
    print("1. Xem danh sách giao dịch")
    print("2. Thêm Thu/Chi mới")
    print("3. Xem danh sách Categories")
    print("4. Khởi tạo lại Database (Reset)")
    print("0. Thoát")
    
    choice = input("Lựa chọn của bạn: ")
    return choice

def show_transactions(manager: FinanceManager):
    txs = manager.get_recent_transactions()
    print("\n--- LỊCH SỬ GIAO DỊCH GẦN ĐÂY ---")
    if not txs:
        print("Chưa có giao dịch nào.")
        return
        
    for t in txs:
        type_str = "[THU]" if t.category_type == 1 else "[CHI]"
        print(f"{t.date} | {type_str} {t.category_name:<12} | {t.amount:>10,.0f} | {t.note or ''}")

def add_new_tx(manager: FinanceManager):
    print("\n--- THÊM GIAO DỊCH MỚI ---")
    
    # Hiển thị categories để chọn
    cats = manager.get_all_categories()
    for i, c in enumerate(cats):
        print(f"{i+1}. ({c.type_mark}) {c.value}")
    
    try:
        cat_idx = int(input("Chọn số danh mục: ")) - 1
        amount = float(input("Nhập số tiền: "))
        note = input("Ghi chú (nhấn Enter để bỏ qua): ")
        
        selected_cat = cats[cat_idx]
        manager.add_transaction(amount, selected_cat.id, note)
        print(">> Thêm thành công!")
    except (ValueError, IndexError) as e:
        print(f"!! Lỗi: {e}")

def main():
    manager = FinanceManager()
    # Đảm bảo DB được khởi tạo
    manager.init_storage()
    
    while True:
        choice = main_menu(manager)
        
        if choice == '1':
            show_transactions(manager)
        elif choice == '2':
            add_new_tx(manager)
        elif choice == '3':
            cats = manager.get_all_categories()
            print("\n--- DANH SÁCH CATEGORIES ---")
            for c in cats:
                print(f"ID: {c.id:<2} | {c.value:<12} | Loại: {c.type_name}")
        elif choice == '4':
            confirm = input("Bạn có chắc muốn Reset Database? (y/n): ")
            if confirm.lower() == 'y':
                manager.reset_data()
        elif choice == '0':
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
