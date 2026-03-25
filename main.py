
from modulo import db_helper, transaction


def menu_chinh():
    print("\n=== QUẢN LÝ TÀI CHÍNH CÁ NHÂN ===")

    # Hiển thị số dư tổng quan ngay khi mở menu.
    thong_ke = transaction.get_balance_summary()
    print(f"Số dư hiện tại: {thong_ke['current_balance']:,.0f} VND")
    print(
        f"(Tổng Thu: {thong_ke['total_income']:,.0f} | "
        f"Tổng Chi: {abs(thong_ke['total_expense']):,.0f})"
    )

    print("-" * 45)
    print("1. Xem danh sách giao dịch")
    print("2. Thêm Thu/Chi mới")
    print("3. Xem danh sách danh mục")
    print("4. Khởi tạo lại cơ sở dữ liệu")
    print("5. Thống kê theo tháng & cảnh báo ngân sách")
    print("6. Tổng kết theo danh mục")
    print("0. Thoát")

    return input("Lựa chọn của bạn: ")


def hien_thi_giao_dich():
    danh_sach_gd = transaction.get_recent_transactions()
    print("\n--- LỊCH SỬ GIAO DỊCH GẦN ĐÂY ---")
    if not danh_sach_gd:
        print("Chưa có giao dịch nào.")
        return

    for gd in danh_sach_gd:
        loai_gd = "[THU]" if gd["category_type"] == 1 else "[CHI]"
        print(
            f"{gd['date']} | {loai_gd} {gd['category_name']:<12} | "
            f"{gd['amount']:>10,.0f} | {gd['note'] or ''}"
        )


def them_giao_dich_moi():
    print("\n--- THÊM GIAO DỊCH MỚI ---")

    danh_muc = db_helper.get_all_categories()
    if not danh_muc:
        print("Chưa có danh mục. Vui lòng kiểm tra dữ liệu hệ thống.")
        return

    for i, dm in enumerate(danh_muc):
        dau_loai = "+" if dm["type"] == 1 else "-"
        print(f"{i + 1}. ({dau_loai}) {dm['value']}")

    try:
        # Chọn danh mục theo số thứ tự trên màn hình.
        vi_tri_danh_muc = int(input("Chọn số danh mục: ")) - 1
        if vi_tri_danh_muc < 0 or vi_tri_danh_muc >= len(danh_muc):
            print("!! Lỗi: Danh mục không hợp lệ.")
            return

        so_tien = float(input("Nhập số tiền: "))

        # Commit 1: dữ liệu nhập phải là số dương.
        if so_tien <= 0:
            print("!! Lỗi: Số tiền phải lớn hơn 0.")
            return

        ghi_chu = input("Ghi chú (nhấn Enter để bỏ qua): ").strip()
        danh_muc_da_chon = danh_muc[vi_tri_danh_muc]

        # add_transaction sẽ tự xử lý dấu âm/dương theo loại category.
        transaction.add_transaction(so_tien, danh_muc_da_chon["id"], ghi_chu)
        print(">> Thêm thành công!")
    except ValueError:
        print("!! Lỗi: Vui lòng nhập đúng định dạng số.")


def hien_thi_bao_cao_thang():
    # Commit 2: thống kê theo tháng + cảnh báo ngân sách.
    print("\n--- THỐNG KÊ THEO THÁNG ---")
    try:
        nam = int(input("Nhập năm (VD: 2026): "))
        thang = int(input("Nhập tháng (1-12): "))

        if thang < 1 or thang > 12:
            print("!! Lỗi: Tháng phải từ 1 đến 12.")
            return

        du_lieu_thang = db_helper.get_monthly_summary(nam, thang)

        tong_thu = 0
        tong_chi = 0
        so_luong_giao_dich = 0

        if du_lieu_thang:
            dong = du_lieu_thang[0]
            tong_thu = dong.get("total_income") or 0
            tong_chi = abs(dong.get("total_expense") or 0)
            so_luong_giao_dich = dong.get("transaction_count") or 0

        han_muc = db_helper.get_budget_limit()
        so_du = tong_thu - tong_chi
        vuot_han_muc = tong_chi > han_muc

        print(f"\nBáo cáo tháng {thang:02d}/{nam}")
        print(f"Tổng thu          : {tong_thu:,.0f} VND")
        print(f"Tổng chi          : {tong_chi:,.0f} VND")
        print(f"Số dư             : {so_du:,.0f} VND")
        print(f"Số lượng giao dịch: {so_luong_giao_dich}")
        print(f"Hạn mức ngân sách : {han_muc:,.0f} VND")

        if vuot_han_muc:
            print("⚠ CẢNH BÁO: Bạn đã vượt ngân sách tháng này!")
        else:
            print("✅ Bạn vẫn trong mức ngân sách.")
    except ValueError:
        print("!! Lỗi: Năm/tháng phải là số.")


def hien_thi_tong_ket_danh_muc():
    # Commit 3: tổng kết theo danh mục
    print("\n--- TỔNG KẾT THEO DANH MỤC ---")
    du_lieu_danh_muc = db_helper.get_category_summary()

    if not du_lieu_danh_muc:
        print("Chưa có dữ liệu giao dịch.")
        return

    print(f"{'LOẠI':<6} | {'DANH MỤC':<14} | {'SỐ GD':<6} | {'TỔNG TIỀN':>12}")
    print("-" * 52)

    # 2 biến để cộng dồn tổng thu và tổng chi
    tong_thu = 0
    tong_chi = 0

    for dong in du_lieu_danh_muc:
        loai = "THU" if dong["category_type"] == 1 else "CHI"
        tong_tien = abs(dong["total_amount"] or 0)

        # Nếu là THU thì cộng vào tong_thu, ngược lại cộng vào tong_chi.
        if dong["category_type"] == 1:
            tong_thu += tong_tien
        else:
            tong_chi += tong_tien

        print(
            f"{loai:<6} | "
            f"{dong['category_name']:<14} | "
            f"{dong['transaction_count']:<6} | "
            f"{tong_tien:>12,.0f}"
        )

    # In thêm dòng tổng kết cuối bảng cho dễ nhìn
    print("-" * 52)
    print(f"Tổng THU theo danh mục: {tong_thu:,.0f} VND")
    print(f"Tổng CHI theo danh mục: {tong_chi:,.0f} VND")


def hien_thi_danh_muc():
    print("\n--- DANH SÁCH DANH MỤC ---")
    danh_muc = db_helper.get_all_categories()

    if not danh_muc:
        print("Chưa có danh mục nào.")
        return

    for dm in danh_muc:
        loai = "Thu nhập" if dm["type"] == 1 else "Chi tiêu"
        print(f"ID: {dm['id']:<2} | {dm['value']:<12} | Loại: {loai}")


def chuong_trinh_chinh():
    # Đảm bảo database được khởi tạo trước khi dùng.
    db_helper.init_db()

    while True:
        lua_chon = menu_chinh()

        if lua_chon == "1":
            hien_thi_giao_dich()
        elif lua_chon == "2":
            them_giao_dich_moi()
        elif lua_chon == "3":
            hien_thi_danh_muc()
        elif lua_chon == "4":
            confirm = input("Bạn có chắc muốn Reset Database? (y/n): ")
            if confirm.lower() == "y":
                db_helper.reset_database()
                print(">> Đã reset database.")
        elif lua_chon == "5":
            hien_thi_bao_cao_thang()
        elif lua_chon == "6":
            hien_thi_tong_ket_danh_muc()
        elif lua_chon == "0":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    chuong_trinh_chinh()