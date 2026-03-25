from datetime import datetime
import random

from flask import Flask, flash, redirect, render_template, request, url_for

from modulo import db_helper, transaction


app = Flask(__name__)
app.secret_key = "money-manager-secret-key"


def tao_du_lieu_demo(dm_thu, ds_dm_chi, so_tien_thu, so_tien_chi_1, so_tien_chi_2, nhan):
    ngay_gio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    transaction.add_transaction(so_tien_thu, dm_thu["id"], f"{nhan}: thu nhập", ngay_gio)
    transaction.add_transaction(so_tien_chi_1, ds_dm_chi[0]["id"], f"{nhan}: chi tiêu 1", ngay_gio)
    transaction.add_transaction(so_tien_chi_2, ds_dm_chi[1]["id"], f"{nhan}: chi tiêu 2", ngay_gio)


def lay_bao_cao_thang(nam, thang):
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
    vuot_han_muc = tong_chi > han_muc

    return {
        "nam": nam,
        "thang": thang,
        "tong_thu": tong_thu,
        "tong_chi": tong_chi,
        "so_du": tong_thu - tong_chi,
        "so_luong_giao_dich": so_luong_giao_dich,
        "han_muc": han_muc,
        "vuot_han_muc": vuot_han_muc,
        "so_tien_vuot": max(tong_chi - han_muc, 0),
    }


@app.get("/")
def trang_chu():
    db_helper.init_db()

    now = datetime.now()
    nam = request.args.get("nam", default=now.year, type=int)
    thang = request.args.get("thang", default=now.month, type=int)

    thong_ke = transaction.get_balance_summary()
    giao_dich = db_helper.get_all_transactions()[:20]
    danh_muc = db_helper.get_all_categories()
    tong_ket_danh_muc = db_helper.get_category_summary()
    bao_cao_thang = lay_bao_cao_thang(nam, thang)

    return render_template(
        "index.html",
        thong_ke=thong_ke,
        giao_dich=giao_dich,
        danh_muc=danh_muc,
        tong_ket_danh_muc=tong_ket_danh_muc,
        bao_cao_thang=bao_cao_thang,
    )


@app.post("/them-giao-dich")
def them_giao_dich():
    try:
        category_id = int(request.form.get("category_id", "0"))
        so_tien = float(request.form.get("amount", "0"))
        ghi_chu = request.form.get("note", "").strip()

        if so_tien <= 0:
            flash("Số tiền phải lớn hơn 0.", "error")
            return redirect(url_for("trang_chu"))

        danh_muc = db_helper.get_all_categories()
        danh_muc_da_chon = next((dm for dm in danh_muc if dm["id"] == category_id), None)
        if not danh_muc_da_chon:
            flash("Danh mục không hợp lệ.", "error")
            return redirect(url_for("trang_chu"))

        transaction.add_transaction(so_tien, category_id, ghi_chu)

        if danh_muc_da_chon["type"] == 1:
            flash(f"Tài khoản vừa nhận {so_tien:,.0f} VND ({danh_muc_da_chon['value']}).", "success")
        else:
            flash(f"Tài khoản đã trừ {so_tien:,.0f} VND ({danh_muc_da_chon['value']}).", "success")

    except ValueError:
        flash("Dữ liệu nhập không hợp lệ.", "error")

    return redirect(url_for("trang_chu"))


@app.post("/cap-nhat-ngan-sach")
def cap_nhat_ngan_sach():
    try:
        han_muc = float(request.form.get("budget_limit", "0"))
        if han_muc <= 0:
            flash("Hạn mức ngân sách phải lớn hơn 0.", "error")
            return redirect(url_for("trang_chu"))

        db_helper.set_budget_limit(han_muc)
        flash(f"Đã cập nhật hạn mức ngân sách: {han_muc:,.0f} VND.", "success")
    except ValueError:
        flash("Giá trị hạn mức không hợp lệ.", "error")

    return redirect(url_for("trang_chu"))


@app.post("/demo-nhanh")
def demo_nhanh():
    mode = request.form.get("mode", "full")

    danh_muc = db_helper.get_all_categories()
    dm_thu = next((dm for dm in danh_muc if dm["type"] == 1), None)
    ds_dm_chi = [dm for dm in danh_muc if dm["type"] == 0][:2]

    if dm_thu is None or len(ds_dm_chi) < 2:
        flash("Danh mục mẫu chưa đủ (cần ít nhất 1 thu và 2 chi).", "error")
        return redirect(url_for("trang_chu"))

    if mode == "normal":
        han_muc_demo = random.randint(1_500_000, 3_000_000)
        db_helper.set_budget_limit(han_muc_demo)
        tao_du_lieu_demo(
            dm_thu,
            ds_dm_chi,
            random.randint(6_000_000, 10_000_000),
            random.randint(80_000, 250_000),
            random.randint(100_000, 300_000),
            "Demo không vượt",
        )
        flash("Đã tạo demo không vượt hạn mức.", "success")
    elif mode == "over":
        han_muc_demo = random.randint(250_000, 500_000)
        db_helper.set_budget_limit(han_muc_demo)
        tao_du_lieu_demo(
            dm_thu,
            ds_dm_chi,
            random.randint(2_000_000, 4_000_000),
            random.randint(250_000, 450_000),
            random.randint(300_000, 650_000),
            "Demo vượt hạn mức",
        )
        flash("Đã tạo demo vượt hạn mức.", "success")
    else:
        db_helper.set_budget_limit(2_500_000)
        tao_du_lieu_demo(
            dm_thu,
            ds_dm_chi,
            random.randint(7_000_000, 10_000_000),
            random.randint(100_000, 250_000),
            random.randint(120_000, 300_000),
            "Demo đầy đủ - không vượt",
        )

        db_helper.set_budget_limit(400_000)
        tao_du_lieu_demo(
            dm_thu,
            ds_dm_chi,
            random.randint(2_500_000, 4_000_000),
            random.randint(250_000, 450_000),
            random.randint(300_000, 650_000),
            "Demo đầy đủ - vượt",
        )
        flash("Đã tạo demo đầy đủ (không vượt + vượt hạn mức).", "success")

    return redirect(url_for("trang_chu"))


@app.post("/reset-demo")
def reset_demo():
    """Reset nhanh dữ liệu để chuẩn bị demo lại từ đầu."""
    db_helper.reset_database()
    flash("Đã reset dữ liệu demo về trạng thái ban đầu.", "success")
    return redirect(url_for("trang_chu"))


if __name__ == "__main__":
    db_helper.init_db()
    app.run(debug=True)
