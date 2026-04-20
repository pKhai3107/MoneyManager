from modulo import db_helper, transaction
from datetime import datetime
import random


def xoa_man_hinh():
    """Xóa màn hình theo hệ điều hành để giao diện CLI gọn hơn."""
    import os
    os.system("cls" if os.name == "nt" else "clear")


def tam_dung(thong_bao="\nNhấn Enter để tiếp tục..."):
    """Tạm dừng để người dùng kịp đọc kết quả trên màn hình."""
    input(thong_bao)


def thong_bao_bien_dong_so_du(danh_muc, so_tien):
    """Hiển thị thông báo biến động số dư theo loại thu/chi."""
    if danh_muc["type"] == 1:
        print(f" Tài khoản của bạn vừa nhận {so_tien:,.0f} VND ({danh_muc['value']}).")
    else:
        print(f" Tài khoản của bạn đã trừ {so_tien:,.0f} VND ({danh_muc['value']}).")


def nhap_so_nguyen(thong_bao):
    """Nhập số nguyên, yêu cầu nhập lại nếu sai định dạng."""
    while True:
        try:
            return int(input(thong_bao))
        except ValueError:
            print("!! Lỗi: Vui lòng nhập số nguyên hợp lệ.")


def nhap_so_tien_duong(thong_bao):
    """Nhập số tiền dương, yêu cầu nhập lại nếu <= 0 hoặc sai định dạng."""
    while True:
        try:
            so_tien = float(input(thong_bao))
            if so_tien <= 0:
                print("!! Lỗi: Số tiền phải lớn hơn 0.")
                continue
            return so_tien
        except ValueError:
            print("!! Lỗi: Vui lòng nhập đúng định dạng số.")


def menu_chinh():
    xoa_man_hinh()
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
    print("7. Demo nhanh (tạo dữ liệu mẫu)")
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

    # Chọn danh mục theo số thứ tự trên màn hình.
    vi_tri_danh_muc = nhap_so_nguyen("Chọn số danh mục: ") - 1
    if vi_tri_danh_muc < 0 or vi_tri_danh_muc >= len(danh_muc):
        print("!! Lỗi: Danh mục không hợp lệ.")
        return

    so_tien = nhap_so_tien_duong("Nhập số tiền: ")
    ghi_chu = input("Ghi chú (nhấn Enter để bỏ qua): ").strip()
    danh_muc_da_chon = danh_muc[vi_tri_danh_muc]

    # add_transaction sẽ tự xử lý dấu âm/dương theo loại category.
    transaction.add_transaction(so_tien, danh_muc_da_chon["id"], ghi_chu)
    print(">> Thêm thành công!")
    thong_bao_bien_dong_so_du(danh_muc_da_chon, so_tien)
    tam_dung()


def hien_thi_bao_cao_thang():
    print("\n--- THỐNG KÊ THEO THÁNG ---")
    nam = nhap_so_nguyen("Nhập năm (VD: 2026): ")
    thang = nhap_so_nguyen("Nhập tháng (1-12): ")

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
        vuot_bao_nhieu = tong_chi - han_muc
        print(f"CẢNH BÁO: Bạn đã vượt ngân sách {vuot_bao_nhieu:,.0f} VND!")
    else:
        print("Bạn vẫn trong mức ngân sách.")
    tam_dung()


def hien_thi_tong_ket_danh_muc():
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
    tam_dung()


def hien_thi_danh_muc():
    print("\n--- DANH SÁCH DANH MỤC ---")
    danh_muc = db_helper.get_all_categories()

    if not danh_muc:
        print("Chưa có danh mục nào.")
        return

    for dm in danh_muc:
        loai = "Thu nhập" if dm["type"] == 1 else "Chi tiêu"
        print(f"ID: {dm['id']:<2} | {dm['value']:<12} | Loại: {loai}")
    tam_dung()


def demo_nhanh():
    """Tạo nhanh dữ liệu mẫu để demo trên lớp mượt hơn."""
    print("\n--- DEMO NHANH: TẠO DỮ LIỆU MẪU ---")

    danh_muc = db_helper.get_all_categories()
    if not danh_muc:
        print("Không tìm thấy danh mục. Hãy kiểm tra dữ liệu hệ thống.")
        tam_dung()
        return

    # Chọn 1 danh mục thu và 2 danh mục chi để tạo dữ liệu mẫu.
    dm_thu = next((dm for dm in danh_muc if dm["type"] == 1), None)
    ds_dm_chi = [dm for dm in danh_muc if dm["type"] == 0][:2]

    if dm_thu is None or len(ds_dm_chi) < 2:
        print("Danh mục mẫu chưa đủ (cần ít nhất 1 thu và 2 chi).")
        tam_dung()
        return

    ngay_gio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Tạo dữ liệu ngẫu nhiên nhưng vẫn hợp lý để demo dễ nhìn.
    thu_ngau_nhien = random.randint(6_000_000, 12_000_000)
    chi_1_ngau_nhien = random.randint(80_000, 300_000)
    chi_2_ngau_nhien = random.randint(120_000, 500_000)

    # Tạo 3 giao dịch mẫu: 1 thu + 2 chi.
    transaction.add_transaction(thu_ngau_nhien, dm_thu["id"], "Demo: thu nhập ngẫu nhiên", ngay_gio)
    transaction.add_transaction(chi_1_ngau_nhien, ds_dm_chi[0]["id"], "Demo: chi tiêu ngẫu nhiên", ngay_gio)
    transaction.add_transaction(chi_2_ngau_nhien, ds_dm_chi[1]["id"], "Demo: chi tiêu ngẫu nhiên", ngay_gio)

    print(">> Đã tạo dữ liệu demo thành công (3 giao dịch ngẫu nhiên).")
    print(f"   + Thu: {thu_ngau_nhien:,.0f} VND ({dm_thu['value']})")
    print(f"   - Chi: {chi_1_ngau_nhien:,.0f} VND ({ds_dm_chi[0]['value']})")
    print(f"   - Chi: {chi_2_ngau_nhien:,.0f} VND ({ds_dm_chi[1]['value']})")
    tam_dung()


def chuong_trinh_chinh():
    # Đảm bảo database được khởi tạo trước khi dùng.
    db_helper.init_db()

    while True:
        lua_chon = menu_chinh()

        if lua_chon == "1":
            hien_thi_giao_dich()
            tam_dung()
        elif lua_chon == "2":
            them_giao_dich_moi()
        elif lua_chon == "3":
            hien_thi_danh_muc()
        elif lua_chon == "4":
            confirm = input("Bạn có chắc muốn Reset Database? (y/n): ")
            if confirm.lower() == "y":
                db_helper.reset_database()
                print(">> Đã reset database.")
            tam_dung()
        elif lua_chon == "5":
            hien_thi_bao_cao_thang()
        elif lua_chon == "6":
            hien_thi_tong_ket_danh_muc()
        elif lua_chon == "7":
            demo_nhanh()
        elif lua_chon == "0":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ.")
            tam_dung()


if __name__ == "__main__":
    chuong_trinh_chinh()