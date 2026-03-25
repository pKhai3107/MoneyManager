from modulo import db_helper, transaction


def main_menu():
    print("\n=== QUẢN LÝ TÀI CHÍNH CÁ NHÂN ===")

    # Lấy số dư nhanh để người dùng nhìn tổng quan ngay khi mở menu
    stats = transaction.get_balance_summary()
    print(f"Số dư hiện tại: {stats['current_balance']:,.0f} VND")
    print(
        f"(Tổng Thu: {stats['total_income']:,.0f} | "
        f"Tổng Chi: {abs(stats['total_expense']):,.0f})"
    )

    print("-" * 45)
    print("1. Xem danh sách giao dịch")
    print("2. Thêm Thu/Chi mới")
    print("3. Xem danh sách Categories")
    print("4. Khởi tạo lại Database (Reset)")
    print("5. Thống kê theo tháng & cảnh báo ngân sách")   # Commit 2
    print("6. Tổng kết theo danh mục")                     # Commit 3
    print("0. Thoát")

    choice = input("Lựa chọn của bạn: ")
    return choice
from modulo import db_helper, transaction


def main_menu():
    print("\n=== QUẢN LÝ TÀI CHÍNH CÁ NHÂN ===")

    # Hiển thị số dư tổng quan ngay khi mở menu.
    stats = transaction.get_balance_summary()
    print(f"Số dư hiện tại: {stats['current_balance']:,.0f} VND")
    print(
        f"(Tổng Thu: {stats['total_income']:,.0f} | "
        f"Tổng Chi: {abs(stats['total_expense']):,.0f})"
    )

    print("-" * 45)
    print("1. Xem danh sách giao dịch")
    print("2. Thêm Thu/Chi mới")
    print("3. Xem danh sách Categories")
    print("4. Khởi tạo lại Database (Reset)")
    print("5. Thống kê theo tháng & cảnh báo ngân sách")
    print("6. Tổng kết theo danh mục")
    print("0. Thoát")

    return input("Lựa chọn của bạn: ")


def show_transactions():
    txs = transaction.get_recent_transactions()
    print("\n--- LỊCH SỬ GIAO DỊCH GẦN ĐÂY ---")
    if not txs:
        print("Chưa có giao dịch nào.")
        return
        
    for t in txs:
        type_str = "[THU]" if t['category_type'] == 1 else "[CHI]"
        print(f"{t['date']} | {type_str} {t['category_name']:<12} | {t['amount']:>10,.0f} | {t['note'] or ''}")

def add_new_tx():
    print("\n--- THÊM GIAO DỊCH MỚI ---")
    
    # Hiển thị categories để chọn
    cats = db_helper.get_all_categories()
    for i, c in enumerate(cats):
        type_mark = "+" if c['type'] == 1 else "-"
        print(f"{i+1}. ({type_mark}) {c['value']}")
    
    try:
        cat_idx = int(input("Chọn số danh mục: ")) - 1
        amount = float(input("Nhập số tiền: "))
        note = input("Ghi chú (nhấn Enter để bỏ qua): ")
        
        selected_cat = cats[cat_idx]
        transaction.add_transaction(amount, selected_cat['id'], note)
        print(">> Thêm thành công!")
    except (ValueError, IndexError):
        print("!! Lỗi: Lựa chọn không hợp lệ.")

def main():
    # Đảm bảo DB được khởi tạo
    db_helper.init_db()
    
    while True:
        choice = main_menu()
        
        if choice == '1':
            show_transactions()
        elif choice == '2':
            add_new_tx()
        elif choice == '3':
            cats = db_helper.get_all_categories()
            print("\n--- DANH SÁCH CATEGORIES ---")
            for c in cats:
                type_name = "Thu nhập" if c['type'] == 1 else "Chi tiêu"
                print(f"ID: {c['id']:<2} | {c['value']:<12} | Loại: {type_name}")
        elif choice == '4':
            confirm = input("Bạn có chắc muốn Reset Database? (y/n): ")
            if confirm.lower() == 'y':
                db_helper.reset_database()
        elif choice == '0':
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
