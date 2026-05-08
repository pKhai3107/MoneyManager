from __future__ import annotations

import calendar
from datetime import datetime
import math
import re
import unicodedata

from flask import Flask, flash, redirect, render_template, request, session, url_for

from modulo import db_helper, transaction


app = Flask(__name__)
app.secret_key = "money-manager-dev-key"


SUPPORTED_LANGUAGES = [
    {"code": "vi", "label": "Tiếng Việt"},
    {"code": "en", "label": "English"},
]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "vi": {
        "language": "Ngôn ngữ",
        "finance_dashboard": "Bảng điều khiển tài chính",
        "dashboard": "Dashboard",
        "transactions": "Giao dịch",
        "categories": "Danh mục",
        "budget": "Ngân sách",
        "reports": "Báo cáo",
        "create_demo": "Tạo demo",
        "reset_data": "Thiết lập lại dữ liệu",
        "add_transaction": "Thêm giao dịch",
        "quick_overview": "Tổng quan nhanh",
        "footer_note": "MoneyManager hỗ trợ báo cáo 6 tháng gần nhất.",
    },
    "en": {
        "language": "Language",
        "finance_dashboard": "Finance dashboard",
        "dashboard": "Dashboard",
        "transactions": "Transactions",
        "categories": "Categories",
        "budget": "Budget",
        "reports": "Reports",
        "create_demo": "Create demo",
        "reset_data": "Reset data",
        "add_transaction": "Add transaction",
        "quick_overview": "Quick overview",
        "footer_note": "MoneyManager includes reports for the latest 6 months.",
    },
}


def _current_language() -> str:
    language = session.get("language", "vi")
    return language if language in TRANSLATIONS else "vi"


def t(key: str) -> str:
    language = _current_language()
    return TRANSLATIONS.get(language, TRANSLATIONS["vi"]).get(key, TRANSLATIONS["vi"].get(key, key))


@app.context_processor
def inject_language_context() -> dict[str, object]:
    return {
        "current_lang": _current_language(),
        "supported_languages": SUPPORTED_LANGUAGES,
        "t": t,
    }


def _format_money(value: float) -> str:
    return f"{value:,.0f}"


app.jinja_env.filters["money"] = _format_money


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "category"


@app.route("/language", methods=["POST"])
def set_language() -> str:
    language = request.form.get("language", "vi")
    session["language"] = language if language in TRANSLATIONS else "vi"
    return redirect(request.referrer or url_for("dashboard"))


def _parse_datetime_local(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")


def _parse_period(value: str | None) -> tuple[int, int, str]:
    today = datetime.now()
    if not value:
        return today.year, today.month, f"{today.year:04d}-{today.month:02d}"

    try:
        year_text, month_text = value.split("-", 1)
        year = int(year_text)
        month = int(month_text)
        if month < 1 or month > 12:
            raise ValueError
        return year, month, f"{year:04d}-{month:02d}"
    except ValueError:
        return today.year, today.month, f"{today.year:04d}-{today.month:02d}"


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    total_months = year * 12 + (month - 1) + offset
    shifted_year = total_months // 12
    shifted_month = total_months % 12 + 1
    return shifted_year, shifted_month


def _month_label(year: int, month: int) -> str:
    return f"Tháng {month:02d}/{year}"


def _build_report_period_options(limit: int = 12) -> list[dict[str, str]]:
    today = datetime.now()
    options = []

    for offset in range(limit):
        year, month = _shift_month(today.year, today.month, -offset)
        value = f"{year:04d}-{month:02d}"
        options.append({"value": value, "label": _month_label(year, month)})

    return options


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, 0, 0, 0)
    end_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, end_day, 23, 59, 59)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def _find_transaction(transaction_id: int) -> dict[str, object] | None:
    return next((item for item in db_helper.get_all_transactions() if item["id"] == transaction_id), None)


def _seed_demo_transactions() -> tuple[bool, str]:
    if db_helper.get_database_stats()["total_transactions"] > 0:
        return False, "Đã có dữ liệu thực tế, không tạo thêm demo."

    categories = {item["key"]: item for item in db_helper.get_all_categories()}
    required_keys = ["salary", "bonus", "food", "transport", "shopping", "bill"]
    if not all(key in categories for key in required_keys):
        return False, "Thiếu danh mục mặc định để tạo dữ liệu demo."

    today = datetime.now()
    current_year, current_month = today.year, today.month
    previous_year, previous_month = _shift_month(current_year, current_month, -1)

    def build_demo_entries(year: int, month: int, income_plan: list[tuple[int, int, str, str]], expense_plan: list[tuple[int, int, str, str]]) -> list[tuple[str, int, int, str]]:
        last_day = calendar.monthrange(year, month)[1]
        entries: list[tuple[str, int, int, str]] = []

        for day, amount, category_key, note_text in income_plan + expense_plan:
            safe_day = min(day, last_day)
            timestamp = f"{year:04d}-{month:02d}-{safe_day:02d}"
            time_part = "08:00:00" if category_key in {"salary", "bonus"} else "12:30:00"
            entries.append((f"{timestamp} {time_part}", amount, categories[category_key]["id"], note_text))

        return entries

    current_income_plan = [
        (1, 780000, "salary", "Lương đầu tháng"),
        (5, 420000, "bonus", "Thu nhập thêm"),
        (9, 650000, "salary", "Khoản cộng tác"),
        (13, 520000, "bonus", "Thưởng nhỏ"),
        (18, 600000, "salary", "Thanh toán công việc"),
        (23, 700000, "bonus", "Hoa hồng"),
        (28, 560000, "salary", "Lương cuối tháng"),
    ]

    current_expense_plan = [
        (2, 180000, "food", "Ăn sáng"),
        (4, 220000, "food", "Ăn trưa"),
        (6, 160000, "transport", "Di chuyển"),
        (8, 240000, "shopping", "Mua sắm nhỏ"),
        (10, 190000, "food", "Cafe"),
        (12, 260000, "bill", "Hóa đơn điện"),
        (14, 170000, "food", "Ăn sáng"),
        (16, 210000, "transport", "Xe cộ"),
        (19, 280000, "shopping", "Mua đồ"),
        (21, 200000, "food", "Ăn trưa"),
        (24, 230000, "bill", "Hóa đơn nước"),
        (27, 180000, "food", "Ăn tối"),
        (29, 250000, "transport", "Di chuyển công việc"),
        (31, 220000, "bill", "Điện thoại"),
    ]

    previous_income_plan = [
        (1, 720000, "salary", "Lương tháng trước"),
        (5, 380000, "bonus", "Thu nhập thêm"),
        (9, 580000, "salary", "Khoản cộng tác"),
        (13, 470000, "bonus", "Thưởng nhỏ"),
        (18, 540000, "salary", "Thanh toán công việc"),
        (23, 640000, "bonus", "Hoa hồng"),
        (28, 500000, "salary", "Lương cuối tháng"),
    ]

    previous_expense_plan = [
        (2, 160000, "food", "Ăn sáng"),
        (4, 200000, "food", "Ăn trưa"),
        (6, 140000, "transport", "Di chuyển"),
        (8, 210000, "shopping", "Mua sắm nhỏ"),
        (10, 170000, "food", "Cafe"),
        (12, 240000, "bill", "Hóa đơn điện"),
        (14, 150000, "food", "Ăn sáng"),
        (16, 180000, "transport", "Xe cộ"),
        (19, 250000, "shopping", "Mua đồ"),
        (21, 190000, "food", "Ăn trưa"),
        (24, 210000, "bill", "Hóa đơn nước"),
        (27, 170000, "food", "Ăn tối"),
        (29, 230000, "transport", "Di chuyển công việc"),
        (31, 200000, "bill", "Điện thoại"),
    ]

    sample_transactions = build_demo_entries(current_year, current_month, current_income_plan, current_expense_plan)
    sample_transactions += build_demo_entries(previous_year, previous_month, previous_income_plan, previous_expense_plan)

    created_count = 0
    for date_value, amount_value, category_id, note_value in sample_transactions:
        transaction.add_transaction(amount_value, category_id, note_value, date_value)
        created_count += 1

    return True, f"Đã tạo {created_count} giao dịch demo."


def _ensure_db() -> None:
    if not app.config.get("DATABASE_READY", False):
        db_helper.init_db()
        app.config["DATABASE_READY"] = True


def _shared_context(active_page: str, page_title: str, page_subtitle: str) -> dict[str, object]:
    _ensure_db()

    stats = db_helper.get_database_stats()
    budget_limit = db_helper.get_budget_limit()
    today = datetime.now()
    month_start, month_end = _month_bounds(today.year, today.month)
    month_transactions = db_helper.get_transactions_by_date_range(month_start, month_end)
    spent = abs(sum(float(item.get("amount") or 0) for item in month_transactions if float(item.get("amount") or 0) < 0))
    budget_used = (spent / budget_limit * 100) if budget_limit else 0
    budget_used = min(budget_used, 100)
    budget_remaining = max(budget_limit - spent, 0)

    recent_transactions = db_helper.get_all_transactions()[:12]
    all_categories = db_helper.get_all_categories()
    expense_categories = [item for item in all_categories if item["type"] == 0]
    income_categories = [item for item in all_categories if item["type"] == 1]
    category_summary = db_helper.get_category_summary()[:8]
    monthly_summary = list(reversed(db_helper.get_monthly_summary()[:6]))

    chart_month_labels = [row["month"] for row in monthly_summary]
    chart_income_values = [float(row["total_income"] or 0) for row in monthly_summary]
    chart_expense_values = [abs(float(row["total_expense"] or 0)) for row in monthly_summary]

    category_labels = [row["category_name"] for row in category_summary]
    category_values = [abs(float(row["total_amount"] or 0)) for row in category_summary]

    return {
        "active_page": active_page,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "stats": stats,
        "budget_limit": budget_limit,
        "budget_spent": spent,
        "budget_used": budget_used,
        "budget_remaining": budget_remaining,
        "recent_transactions": recent_transactions,
        "all_categories": all_categories,
        "expense_categories": expense_categories,
        "income_categories": income_categories,
        "category_summary": category_summary,
        "monthly_summary": monthly_summary,
        "chart_month_labels": chart_month_labels,
        "chart_income_values": chart_income_values,
        "chart_expense_values": chart_expense_values,
        "category_labels": category_labels,
        "category_values": category_values,
        "current_balance_display": _format_money(stats["current_balance"]),
        "total_income_display": _format_money(stats["total_income"]),
        "total_expense_display": _format_money(abs(stats["total_expense"])),
    }


def _transaction_form_context(active_page: str, page_title: str, page_subtitle: str, search_query: str = "") -> dict[str, object]:
    context = _shared_context(active_page, page_title, page_subtitle)
    all_transactions = db_helper.get_all_transactions()
    transaction_type_filter = request.args.get("type", default="all")
    page = request.args.get("page", default=1, type=int) or 1
    per_page = 10

    type_counts = {
        "all": len(all_transactions),
        "income": sum(1 for item in all_transactions if item["category_type"] == 1),
        "expense": sum(1 for item in all_transactions if item["category_type"] == 0),
    }

    if transaction_type_filter not in ("all", "income", "expense"):
        transaction_type_filter = "all"

    if transaction_type_filter == "income":
        typed_transactions = [item for item in all_transactions if item["category_type"] == 1]
    elif transaction_type_filter == "expense":
        typed_transactions = [item for item in all_transactions if item["category_type"] == 0]
    else:
        typed_transactions = all_transactions

    query = search_query.strip().lower()
    if query:
        filtered_transactions = [
            item
            for item in typed_transactions
            if query in str(item.get("category_name", "")).lower()
            or query in str(item.get("note", "")).lower()
            or query in str(item.get("date", "")).lower()
            or query in f"{item.get('amount', 0):,.0f}".lower()
        ]
    else:
        filtered_transactions = typed_transactions

    total_income = sum(float(item.get("amount") or 0) for item in filtered_transactions if float(item.get("amount") or 0) > 0)
    total_expense = abs(sum(float(item.get("amount") or 0) for item in filtered_transactions if float(item.get("amount") or 0) < 0))
    total_net = total_income - total_expense

    total_items = len(filtered_transactions)
    total_pages = max(1, int(math.ceil(total_items / per_page))) if per_page else 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_transactions = filtered_transactions[start_index:end_index]
    selected_transaction = paginated_transactions[0] if paginated_transactions else None

    display_start = start_index + 1 if total_items else 0
    display_end = min(end_index, total_items) if total_items else 0

    context.update(
        {
            "search_query": search_query,
            "transaction_type_filter": transaction_type_filter,
            "transaction_type_counts": type_counts,
            "transactions": paginated_transactions,
            "selected_transaction": selected_transaction,
            "transaction_count_display": total_items,
            "transactions_total_income": total_income,
            "transactions_total_expense": total_expense,
            "transactions_total_net": total_net,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "display_start": display_start,
                "display_end": display_end,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1,
                "next_page": page + 1,
            },
        }
    )
    return context


@app.route("/")
def dashboard() -> str:
    return render_template(
        "dashboard.html",
        **_shared_context(
            "dashboard",
            "Tổng quan tài chính",
            "Bảng điều khiển trực quan với số dư, xu hướng và phân bổ theo danh mục.",
        ),
    )


@app.route("/transactions")
def transactions_page() -> str:
    search_query = request.args.get("q", default="").strip()
    return render_template(
        "transactions.html",
        **_transaction_form_context(
            "transactions",
            "Giao dịch",
            "Quản lý thu - chi theo từng giao dịch và thêm mới nhanh trên một màn hình riêng.",
            search_query,
        ),
    )


@app.route("/transactions/add", methods=["POST"])
def add_transaction() -> str:
    category_id = request.form.get("category_id", type=int)
    amount = request.form.get("amount", type=float)
    note = request.form.get("note", default="").strip() or None
    date_value = _parse_datetime_local(request.form.get("date"))

    if category_id is None or amount is None:
        flash("Vui lòng nhập số tiền và chọn danh mục.", "error")
        return redirect(url_for("transactions_page"))

    try:
        transaction.add_transaction(amount, category_id, note, date_value)
        flash("Đã thêm giao dịch thành công.", "success")
    except ValueError as exc:
        flash(str(exc), "error")

    return redirect(url_for("transactions_page"))


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
def edit_transaction(transaction_id: int) -> str:
    transaction_row = _find_transaction(transaction_id)
    if transaction_row is None:
        flash("Không tìm thấy giao dịch cần sửa.", "error")
        return redirect(url_for("transactions_page"))

    categories = db_helper.get_all_categories()

    if request.method == "POST":
        category_id = request.form.get("category_id", type=int)
        amount = request.form.get("amount", type=float)
        note = request.form.get("note", default="").strip() or None
        date_value = _parse_datetime_local(request.form.get("date"))

        if category_id is None or amount is None or not date_value:
            flash("Vui lòng nhập đầy đủ thông tin giao dịch.", "error")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        selected_category = next((item for item in categories if item["id"] == category_id), None)
        if selected_category is None:
            flash("Danh mục không hợp lệ.", "error")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        final_amount = abs(amount) if selected_category["type"] == 1 else -abs(amount)
        db_helper.update_transaction(
            transaction_id,
            date=date_value,
            amount=final_amount,
            category_id=category_id,
            note=note,
        )
        flash("Đã cập nhật giao dịch.", "success")
        return redirect(url_for("transactions_page"))

    return render_template(
        "transaction_edit.html",
        **_shared_context(
            "transactions",
            "Sửa giao dịch",
            "Cập nhật lại nội dung giao dịch, danh mục và thời gian khi cần.",
        ),
        transaction_row=transaction_row,
        categories=categories,
    )


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
def delete_transaction(transaction_id: int) -> str:
    if db_helper.delete_transaction(transaction_id):
        flash("Đã xóa giao dịch.", "success")
    else:
        flash("Không thể xóa giao dịch.", "error")
    return redirect(url_for("transactions_page"))


@app.route("/categories")
def categories_page() -> str:
    return render_template(
        "categories.html",
        **_shared_context(
            "categories",
            "Danh mục",
            "Tách riêng nhóm thu - chi để dữ liệu rõ ràng và dễ mở rộng hơn.",
        ),
    )


@app.route("/categories/add", methods=["POST"])
def add_category() -> str:
    category_name = request.form.get("category_name", default="").strip()
    category_type = request.form.get("category_type", type=int)

    if not category_name or category_type not in (0, 1):
        flash("Vui lòng nhập tên danh mục và chọn loại danh mục.", "error")
        return redirect(url_for("categories_page"))

    category_key = request.form.get("key", default="").strip().lower() or _slugify(category_name)
    created_id = db_helper.create_category(category_key, category_name, category_type)

    if created_id is None:
        flash("Danh mục này đã tồn tại, vui lòng đổi tên hoặc mã khác.", "error")
    else:
        flash("Đã thêm danh mục mới thành công.", "success")

    return redirect(url_for("categories_page"))


@app.route("/categories/delete", methods=["POST"])
def delete_category() -> str:
    key = request.form.get("key", default="").strip()
    if not key:
        flash("Thiếu mã danh mục cần xóa.", "error")
        return redirect(url_for("categories_page"))

    if db_helper.delete_category(key):
        flash("Đã xóa danh mục.", "success")
    else:
        flash("Không thể xóa danh mục vì đang có giao dịch sử dụng.", "error")

    return redirect(url_for("categories_page"))


@app.route("/budget")
def budget_page() -> str:
    return render_template(
        "budget.html",
        **_shared_context(
            "budget",
            "Ngân sách",
            "Theo dõi hạn mức chi tiêu, mức sử dụng và xu hướng tài chính theo tháng.",
        ),
    )


@app.route("/reports")
def reports_page() -> str:
    period_value = request.args.get("period")
    year, month, normalized_period = _parse_period(period_value)
    previous_year, previous_month = _shift_month(year, month, -1)
    recent_page = request.args.get("recent_page", default=1, type=int) or 1
    recent_per_page = 5
    category_page = request.args.get("category_page", default=1, type=int) or 1
    category_per_page = 5
    start_date, end_date = _month_bounds(year, month)
    selected_transactions = db_helper.get_transactions_by_date_range(start_date, end_date)

    # Filter out transactions whose note indicates a chat-based edit (e.g. "chat edit", "chat-edit", "chat_edit")
    chat_edit_pattern = re.compile(r"chat[-_\s]?edit", re.IGNORECASE)
    visible_transactions = [t for t in selected_transactions if not chat_edit_pattern.search(str(t.get("note", "")))]

    previous_start_date, previous_end_date = _month_bounds(previous_year, previous_month)
    previous_transactions = db_helper.get_transactions_by_date_range(previous_start_date, previous_end_date)

    # Also filter previous period transactions for visibility in the timeline/count
    visible_previous = [t for t in previous_transactions if not chat_edit_pattern.search(str(t.get("note", "")))]

    total_income = sum(float(item["amount"] or 0) for item in selected_transactions if float(item["amount"] or 0) > 0)
    total_expense = abs(sum(float(item["amount"] or 0) for item in selected_transactions if float(item["amount"] or 0) < 0))
    net_balance = total_income - total_expense

    previous_income = sum(float(item["amount"] or 0) for item in previous_transactions if float(item["amount"] or 0) > 0)
    previous_expense = abs(sum(float(item["amount"] or 0) for item in previous_transactions if float(item["amount"] or 0) < 0))
    previous_net_balance = previous_income - previous_expense

    def _delta_label(current_value: float, previous_value: float) -> tuple[str, str, float]:
        delta_value = current_value - previous_value
        if previous_value == 0:
            if current_value == 0:
                return "Không đổi", "flat", 0
            return "Mới phát sinh", "up", 100
        return f"{abs(delta_value) / previous_value * 100:.1f}%", "up" if delta_value >= 0 else "down", delta_value

    income_delta_text, income_delta_trend, income_delta_value = _delta_label(total_income, previous_income)
    expense_delta_text, expense_delta_trend, expense_delta_value = _delta_label(total_expense, previous_expense)
    balance_delta_text, balance_delta_trend, balance_delta_value = _delta_label(net_balance, previous_net_balance)
    # Use visible transaction counts (excluding chat-edit notes) for the "Số giao dịch" comparison
    count_delta_text, count_delta_trend, count_delta_value = _delta_label(len(visible_transactions), len(visible_previous))

    day_income: dict[str, float] = {}
    day_expense: dict[str, float] = {}
    for item in selected_transactions:
        day_key = str(item["date"])[:10]
        amount = float(item["amount"] or 0)
        if amount >= 0:
            day_income[day_key] = day_income.get(day_key, 0) + amount
        else:
            day_expense[day_key] = day_expense.get(day_key, 0) + abs(amount)

    days_in_month = calendar.monthrange(year, month)[1]
    day_labels = [f"{day:02d}" for day in range(1, days_in_month + 1)]
    report_income_series = [day_income.get(f"{year:04d}-{month:02d}-{day:02d}", 0) for day in range(1, days_in_month + 1)]
    report_expense_series = [day_expense.get(f"{year:04d}-{month:02d}-{day:02d}", 0) for day in range(1, days_in_month + 1)]

    category_summary = db_helper.get_category_summary(start_date, end_date)
    category_values = [abs(float(item["total_amount"] or 0)) for item in category_summary]
    category_total = sum(category_values)
    category_percentages = [round((value / category_total) * 100, 1) if category_total else 0 for value in category_values]
    monthly_summary = list(reversed(db_helper.get_monthly_summary()[:6]))

    category_total_items = len(category_summary)
    category_total_pages = max(1, int(math.ceil(category_total_items / category_per_page))) if category_per_page else 1
    if category_page < 1:
        category_page = 1
    if category_page > category_total_pages:
        category_page = category_total_pages

    category_start_index = (category_page - 1) * category_per_page
    category_end_index = category_start_index + category_per_page
    report_category_summary_page = category_summary[category_start_index:category_end_index]

    category_display_start = category_start_index + 1 if category_total_items else 0
    category_display_end = min(category_end_index, category_total_items) if category_total_items else 0

    # Recent list and pagination should reflect visible transactions only
    recent_total_items = len(visible_transactions)
    recent_total_pages = max(1, int(math.ceil(recent_total_items / recent_per_page))) if recent_per_page else 1
    if recent_page < 1:
        recent_page = 1
    if recent_page > recent_total_pages:
        recent_page = recent_total_pages

    recent_start_index = (recent_page - 1) * recent_per_page
    recent_end_index = recent_start_index + recent_per_page
    recent_report_transactions = visible_transactions[recent_start_index:recent_end_index]

    recent_display_start = recent_start_index + 1 if recent_total_items else 0
    recent_display_end = min(recent_end_index, recent_total_items) if recent_total_items else 0

    comparison_chart_labels = ["Thu", "Chi", "Số dư"]
    comparison_current_values = [total_income, total_expense, net_balance]
    comparison_previous_values = [previous_income, previous_expense, previous_net_balance]

    return render_template(
        "reports.html",
        **_shared_context(
            "reports",
            "Báo cáo",
            "Biểu đồ và bộ lọc theo tháng để xem rõ hơn bức tranh tài chính cá nhân.",
        ),
        report_period_options=_build_report_period_options(),
        period=normalized_period,
        selected_period_label=_month_label(year, month),
        previous_period_label=_month_label(previous_year, previous_month),
        selected_year=year,
        selected_month=month,
        selected_transactions=selected_transactions,
        recent_report_transactions=recent_report_transactions,
        total_income=total_income,
        total_expense=total_expense,
        net_balance=net_balance,
        previous_income=previous_income,
        previous_expense=previous_expense,
        previous_net_balance=previous_net_balance,
        comparison_cards=[
            {
                "title": "Tổng thu",
                "current": total_income,
                "previous": previous_income,
                "delta_text": income_delta_text,
                "delta_trend": income_delta_trend,
                "delta_value": income_delta_value,
            },
            {
                "title": "Tổng chi",
                "current": total_expense,
                "previous": previous_expense,
                "delta_text": expense_delta_text,
                "delta_trend": expense_delta_trend,
                "delta_value": expense_delta_value,
            },
            {
                "title": "Số dư ròng",
                "current": net_balance,
                "previous": previous_net_balance,
                "delta_text": balance_delta_text,
                "delta_trend": balance_delta_trend,
                "delta_value": balance_delta_value,
            },
            {
                "title": "Số giao dịch",
                "current": len(selected_transactions),
                "previous": len(previous_transactions),
                "delta_text": count_delta_text,
                "delta_trend": count_delta_trend,
                "delta_value": count_delta_value,
            },
        ],
        day_labels=day_labels,
        report_income_series=report_income_series,
        report_expense_series=report_expense_series,
        report_category_labels=[item["category_name"] for item in category_summary],
        report_category_values=category_values,
        report_category_percentages=category_percentages,
        report_category_legend_labels=[
            f"{item['category_name']} ({percent:.1f}%)" if category_total else item["category_name"]
            for item, percent in zip(category_summary, category_percentages)
        ],
        report_category_summary=report_category_summary_page,
        category_pagination={
            "page": category_page,
            "per_page": category_per_page,
            "total_items": category_total_items,
            "total_pages": category_total_pages,
            "display_start": category_display_start,
            "display_end": category_display_end,
            "has_prev": category_page > 1,
            "has_next": category_page < category_total_pages,
            "prev_page": category_page - 1,
            "next_page": category_page + 1,
        },
        report_monthly_labels=[item["month"] for item in monthly_summary],
        report_monthly_income=[float(item["total_income"] or 0) for item in monthly_summary],
        report_monthly_expense=[abs(float(item["total_expense"] or 0)) for item in monthly_summary],
        comparison_chart_labels=comparison_chart_labels,
        comparison_current_values=comparison_current_values,
        comparison_previous_values=comparison_previous_values,
        recent_pagination={
            "page": recent_page,
            "per_page": recent_per_page,
            "total_items": recent_total_items,
            "total_pages": recent_total_pages,
            "display_start": recent_display_start,
            "display_end": recent_display_end,
            "has_prev": recent_page > 1,
            "has_next": recent_page < recent_total_pages,
            "prev_page": recent_page - 1,
            "next_page": recent_page + 1,
        },
    )


@app.route("/budget/update", methods=["POST"])
def update_budget() -> str:
    budget_value = request.form.get("budget_limit", type=float)
    if budget_value is None or budget_value < 0:
        flash("Ngân sách không hợp lệ.", "error")
        return redirect(url_for("budget_page"))

    db_helper.set_budget_limit(budget_value)
    flash("Đã cập nhật hạn mức ngân sách.", "success")
    return redirect(url_for("budget_page"))


@app.route("/reset", methods=["POST"])
def reset_database() -> str:
    db_helper.reset_database()
    app.config["DATABASE_READY"] = True
    flash("Đã khởi tạo lại cơ sở dữ liệu.", "success")
    return redirect(url_for("dashboard"))


@app.route("/demo-data", methods=["POST"])
def create_demo_data() -> str:
    db_helper.reset_database()
    app.config["DATABASE_READY"] = True
    created, message = _seed_demo_transactions()
    flash(message if created else "Không tạo được dữ liệu demo.", "success" if created else "error")
    return redirect(url_for("reports_page"))


if __name__ == "__main__":
    app.run(debug=True)