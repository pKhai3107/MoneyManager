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
        type_str = "[THU]" if t["category_type"] == 1 else "[CHI]"
        print(
            f"{t['date']} | {type_str} {t['category_name']:<12} | "
            f"{t['amount']:>10,.0f} | {t['note'] or ''}"
        )


def add_new_tx():
    print("\n--- THÊM GIAO DỊCH MỚI ---")

    cats = db_helper.get_all_categories()
    if not cats:
        print("Chưa có danh mục. Vui lòng kiểm tra dữ liệu hệ thống.")
        return

    for i, c in enumerate(cats):
        type_mark = "+" if c["type"] == 1 else "-"
        print(f"{i + 1}. ({type_mark}) {c['value']}")

    try:
        # Chọn danh mục theo số thứ tự trên màn hình.
        cat_idx = int(input("Chọn số danh mục: ")) - 1
        if cat_idx < 0 or cat_idx >= len(cats):
            print("!! Lỗi: Danh mục không hợp lệ.")
            return

        amount = float(input("Nhập số tiền: "))

        # Commit 1: dữ liệu nhập phải là số dương.
        if amount <= 0:
            print("!! Lỗi: Số tiền phải lớn hơn 0.")
            return

        note = input("Ghi chú (nhấn Enter để bỏ qua): ").strip()
        selected_cat = cats[cat_idx]

        # add_transaction sẽ tự xử lý dấu âm/dương theo loại category.
        transaction.add_transaction(amount, selected_cat["id"], note)
        print(">> Thêm thành công!")
    except ValueError:
        print("!! Lỗi: Vui lòng nhập đúng định dạng số.")


def show_monthly_report():
    # Commit 2: thống kê theo tháng + cảnh báo ngân sách.
    print("\n--- THỐNG KÊ THEO THÁNG ---")
    try:
        year = int(input("Nhập năm (VD: 2026): "))
        month = int(input("Nhập tháng (1-12): "))

        if month < 1 or month > 12:
            print("!! Lỗi: Tháng phải từ 1 đến 12.")
            return

        monthly_rows = db_helper.get_monthly_summary(year, month)

        total_income = 0
        total_expense = 0
        tx_count = 0

        if monthly_rows:
            row = monthly_rows[0]
            total_income = row.get("total_income") or 0
            total_expense = abs(row.get("total_expense") or 0)
            tx_count = row.get("transaction_count") or 0

        budget_limit = db_helper.get_budget_limit()
        balance = total_income - total_expense
        is_over_budget = total_expense > budget_limit

        print(f"\nBáo cáo tháng {month:02d}/{year}")
        print(f"Tổng thu          : {total_income:,.0f} VND")
        print(f"Tổng chi          : {total_expense:,.0f} VND")
        print(f"Số dư             : {balance:,.0f} VND")
        print(f"Số lượng giao dịch: {tx_count}")
        print(f"Hạn mức ngân sách : {budget_limit:,.0f} VND")

        if is_over_budget:
            print("⚠ CẢNH BÁO: Bạn đã vượt ngân sách tháng này!")
        else:
            print("✅ Bạn vẫn trong mức ngân sách.")
    except ValueError:
        print("!! Lỗi: Năm/tháng phải là số.")


def show_category_summary():
    # Commit 3: tổng kết theo danh mục.
    print("\n--- TỔNG KẾT THEO DANH MỤC ---")
    rows = db_helper.get_category_summary()

    if not rows:
        print("Chưa có dữ liệu giao dịch.")
        return

    print(f"{'LOẠI':<6} | {'DANH MỤC':<14} | {'SỐ GD':<6} | {'TỔNG TIỀN':>12}")
    print("-" * 52)

    for r in rows:
        type_name = "THU" if r["category_type"] == 1 else "CHI"
        total_amount = abs(r["total_amount"] or 0)
        print(
            f"{type_name:<6} | "
            f"{r['category_name']:<14} | "
            f"{r['transaction_count']:<6} | "
            f"{total_amount:>12,.0f}"
        )


def show_categories():
    cats = db_helper.get_all_categories()
    print("\n--- DANH SÁCH CATEGORIES ---")
    if not cats:
        print("Chưa có danh mục nào.")
        return

    for c in cats:
        type_name = "Thu nhập" if c["type"] == 1 else "Chi tiêu"
        print(f"ID: {c['id']:<2} | {c['value']:<12} | Loại: {type_name}")


def main():
    # Đảm bảo database được khởi tạo trước khi dùng.
    db_helper.init_db()

    while True:
        choice = main_menu()

        if choice == "1":
            show_transactions()
        elif choice == "2":
            add_new_tx()
        elif choice == "3":
            show_categories()
        elif choice == "4":
            confirm = input("Bạn có chắc muốn Reset Database? (y/n): ")
            if confirm.lower() == "y":
                db_helper.reset_database()
                print(">> Đã reset database.")
        elif choice == "5":
            show_monthly_report()
        elif choice == "6":
            show_category_summary()
        elif choice == "0":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    main()