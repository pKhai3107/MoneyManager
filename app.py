from __future__ import annotations

import calendar
from datetime import datetime
import json
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Callable

from flask import Flask, flash, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from modulo import db_helper, transaction


app = Flask(__name__)
app.secret_key = os.environ.get("MONEY_MANAGER_SECRET_KEY", "money-manager-dev-key")
finance_manager = transaction.FinanceManager()


SUPPORTED_LANGUAGES = [
    {"code": "vi"},
    {"code": "en"},
]

_I18N_DIR = Path(__file__).with_name("i18n")


def _load_file_translations() -> dict[str, dict[str, str]]:
    loaded: dict[str, dict[str, str]] = {}
    for language in ("vi", "en"):
        file_path = _I18N_DIR / f"{language}.json"
        if not file_path.exists():
            continue
        try:
            loaded[language] = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded[language] = {}
    return loaded


FILE_TRANSLATIONS = _load_file_translations()

_NOTE_TRANSLATION_KEYS = {
    value: key
    for translation_map in FILE_TRANSLATIONS.values()
    for key, value in translation_map.items()
    if key.startswith("demo_note_")
}

_SUMMARY_CACHE_KEY = "summary_cache"
_SUMMARY_CACHE_TTL_SECONDS = 60


def _current_language() -> str:
    language = session.get("language", "vi")
    return language if language in FILE_TRANSLATIONS else "vi"


def t(key: str) -> str:
    language = _current_language()
    return FILE_TRANSLATIONS.get(language, FILE_TRANSLATIONS.get("vi", {})).get(key, key)


@app.context_processor
def inject_language_context() -> dict[str, object]:
    return {
        "current_lang": _current_language(),
        "supported_languages": [
            {
                "code": option["code"],
                "label": t("language_vi") if option["code"] == "vi" else t("language_en"),
            }
            for option in SUPPORTED_LANGUAGES
        ],
        "t": t,
        "category_label": _category_label,
        "note_label": _note_label,
    }


def _format_money(value: float) -> str:
    return f"{value:,.0f}"


app.jinja_env.filters["money"] = _format_money


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "category"


def _category_label(category_key: str, fallback: str | None = None) -> str:
    label_key = f"category_label_{category_key}"
    label = t(label_key)
    if label != label_key:
        return label
    return fallback or category_key


def _note_label(note_text: str | None) -> str:
    if not note_text:
        return ""

    translation_key = _NOTE_TRANSLATION_KEYS.get(note_text)
    return t(translation_key) if translation_key else note_text


@app.route("/language", methods=["POST"])
def set_language() -> str:
    language = request.form.get("language", "vi")
    session["language"] = language if language in FILE_TRANSLATIONS else "vi"
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/favicon.ico")
def favicon() -> object:
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


def _parse_datetime_local(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


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
    return f"{t('month_label_prefix')} {month:02d}/{year}"


def _flash_message(key: str, **values: object) -> str:
    template = t(key)
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def _invalidate_summary_cache() -> None:
    session.pop(_SUMMARY_CACHE_KEY, None)
    session.modified = True


def _cached_summary(cache_key: str, builder: Callable[[], object], ttl_seconds: int = _SUMMARY_CACHE_TTL_SECONDS) -> object:
    request_cache = getattr(g, "summary_cache", None)
    if request_cache is None:
        request_cache = {}
        g.summary_cache = request_cache

    if cache_key in request_cache:
        return request_cache[cache_key]

    session_cache = session.get(_SUMMARY_CACHE_KEY, {})
    cached_entry = session_cache.get(cache_key)
    now = datetime.utcnow().timestamp()
    if isinstance(cached_entry, dict):
        cached_at = float(cached_entry.get("cached_at", 0))
        if now - cached_at <= ttl_seconds and "value" in cached_entry:
            request_cache[cache_key] = cached_entry["value"]
            return cached_entry["value"]

    value = builder()
    request_cache[cache_key] = value
    session_cache[cache_key] = {"cached_at": now, "value": value}
    session[_SUMMARY_CACHE_KEY] = session_cache
    session.modified = True
    return value


def _cached_monthly_summary(limit: int = 6) -> list[dict[str, object]]:
    return _cached_summary(f"monthly_summary_{limit}", lambda: list(reversed(db_helper.get_monthly_summary()[:limit])))  # type: ignore[return-value]


def _cached_category_summary(limit: int = 8) -> list[dict[str, object]]:
    return _cached_summary(f"category_summary_{limit}", lambda: db_helper.get_category_summary()[:limit])  # type: ignore[return-value]


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
    return db_helper.get_transaction_by_id(transaction_id)


def _dashboard_chart_payload(
    monthly_summary: list[dict[str, object]],
    category_summary: list[dict[str, object]],
) -> dict[str, list[object]]:

    return {
        "chart_month_labels": [row["month"] for row in monthly_summary],
        "chart_income_values": [float(row["total_income"] or 0) for row in monthly_summary],
        "chart_expense_values": [abs(float(row["total_expense"] or 0)) for row in monthly_summary],
        "category_labels": [_category_label(str(row.get("category_key", "")), row["category_name"]) for row in category_summary],
        "category_values": [abs(float(row["total_amount"] or 0)) for row in category_summary],
    }


def _seed_demo_transactions() -> tuple[bool, str]:
    if db_helper.get_database_stats()["total_transactions"] > 0:
        return False, t("demo_data_exists")

    categories = {item["key"]: item for item in db_helper.get_all_categories()}
    required_keys = ["salary", "bonus", "food", "transport", "shopping", "bill"]
    if not all(key in categories for key in required_keys):
        return False, t("demo_categories_missing")

    demo_end = datetime(2026, 5, 10, 20, 0, 0)

    sample_transactions: list[tuple[str, int, int, str]] = []
    month_offsets = list(range(-5, 1))

    for month_index, offset in enumerate(month_offsets):
        year, month = _shift_month(demo_end.year, demo_end.month, offset)
        last_day = calendar.monthrange(year, month)[1]
        max_day = demo_end.day if (year == demo_end.year and month == demo_end.month) else last_day

        income_days = [1, 5, 9]
        expense_days = [2, 4, 6, 8, 10]

        income_plan = [
            (income_days[0], 640000 + month_index * 35000, "salary", t("demo_note_part_time_salary")),
            (income_days[1], 320000 + month_index * 25000, "bonus", t("demo_note_extra_income")),
            (income_days[2], 280000 + month_index * 20000, "salary", t("demo_note_tutoring")),
        ]
        expense_plan = [
            (expense_days[0], 140000 + month_index * 10000, "food", t("demo_note_food")),
            (expense_days[1], 110000 + month_index * 9000, "transport", t("demo_note_transport")),
            (expense_days[2], 180000 + month_index * 11000, "shopping", t("demo_note_shopping")),
            (expense_days[3], 160000 + month_index * 7000, "bill", t("demo_note_bill")),
            (expense_days[4], 90000 + month_index * 6000, "food", t("demo_note_snack")),
        ]

        for day, amount, category_key, note_text in income_plan + expense_plan:
            if day > max_day:
                continue

            timestamp = f"{year:04d}-{month:02d}-{day:02d}"
            time_part = "08:30:00" if category_key in {"salary", "bonus"} else "19:00:00"
            sample_transactions.append((f"{timestamp} {time_part}", amount, categories[category_key]["id"], note_text))

    created_count = 0
    for date_value, amount_value, category_id, note_value in sample_transactions:
        finance_manager.add_transaction(amount_value, category_id, note_value, date_value)
        created_count += 1

    return True, _flash_message("demo_transactions_created", count=created_count)


def _ensure_db() -> None:
    if not app.config.get("DATABASE_READY", False):
        db_helper.init_db()
        app.config["DATABASE_READY"] = True


def _shared_context(
    active_page: str,
    page_title: str,
    page_subtitle: str,
) -> dict[str, object]:
    _ensure_db()

    stats = db_helper.get_database_stats()
    budget_limit = db_helper.get_budget_limit()
    today = datetime.now()
    month_start, month_end = _month_bounds(today.year, today.month)
    month_summary = _cached_summary(
        "current_month_budget_summary",
        lambda: db_helper.get_period_summary(month_start, month_end),
    )
    spent = float(month_summary["total_expense"])
    budget_used = (spent / budget_limit * 100) if budget_limit else 0
    budget_used = min(budget_used, 100)
    budget_remaining = max(budget_limit - spent, 0)

    all_categories: list[dict[str, object]] = []
    expense_categories: list[dict[str, object]] = []
    income_categories: list[dict[str, object]] = []
    if active_page in {"transactions", "categories"}:
        all_categories = db_helper.get_all_categories()
        expense_categories = [item for item in all_categories if item["type"] == 0]
        income_categories = [item for item in all_categories if item["type"] == 1]

    chart_payload = {"chart_month_labels": [], "chart_income_values": [], "chart_expense_values": [], "category_labels": [], "category_values": []}

    if active_page == "dashboard":
        monthly_summary = _cached_monthly_summary()
        category_summary = _cached_category_summary()
        chart_payload = _dashboard_chart_payload(monthly_summary, category_summary)

    return {
        "active_page": active_page,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "stats": stats,
        "budget_limit": budget_limit,
        "budget_spent": spent,
        "budget_used": budget_used,
        "budget_remaining": budget_remaining,
        "all_categories": all_categories,
        "expense_categories": expense_categories,
        "income_categories": income_categories,
        "chart_month_labels": chart_payload["chart_month_labels"],
        "chart_income_values": chart_payload["chart_income_values"],
        "chart_expense_values": chart_payload["chart_expense_values"],
        "category_labels": chart_payload["category_labels"],
        "category_values": chart_payload["category_values"],
        "current_balance_display": _format_money(stats["current_balance"]),
        "total_income_display": _format_money(stats["total_income"]),
        "total_expense_display": _format_money(abs(stats["total_expense"])),
    }


@app.route("/api/dashboard-chart-data")
def dashboard_chart_data() -> object:
    _ensure_db()
    return jsonify(_dashboard_chart_payload())


def _transaction_form_context(active_page: str, page_title: str, page_subtitle: str, search_query: str = "") -> dict[str, object]:
    context = _shared_context(active_page, page_title, page_subtitle)
    transaction_type_filter = request.args.get("type", default="all")
    page = request.args.get("page", default=1, type=int) or 1
    per_page = 10

    if transaction_type_filter not in ("all", "income", "expense"):
        transaction_type_filter = "all"
    page_data = db_helper.get_transactions_page(transaction_type_filter, search_query, page, per_page)
    total_items = page_data["total_items"]
    total_pages = max(1, int(math.ceil(total_items / per_page))) if per_page else 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    if page != request.args.get("page", default=1, type=int) and total_items:
        page_data = db_helper.get_transactions_page(transaction_type_filter, search_query, page, per_page)

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_transactions = page_data["transactions"]

    display_start = start_index + 1 if total_items else 0
    display_end = min(end_index, total_items) if total_items else 0

    context.update(
        {
            "search_query": search_query,
            "transaction_type_filter": transaction_type_filter,
            "transaction_type_counts": page_data["type_counts"],
            "transactions": paginated_transactions,
            "transaction_count_display": total_items,
            "transactions_total_income": page_data["total_income"],
            "transactions_total_expense": page_data["total_expense"],
            "transactions_total_net": page_data["total_income"] - page_data["total_expense"],
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


def _summary_chart_data() -> dict[str, list[object]]:
    monthly_summary = _cached_monthly_summary()
    category_summary = _cached_category_summary()
    return _dashboard_chart_payload(monthly_summary, category_summary)


@app.route("/")
def dashboard() -> str:
    return render_template(
        "dashboard.html",
        **_shared_context(
            "dashboard",
            t("dashboard_title"),
            t("dashboard_subtitle"),
        ),
    )


@app.route("/transactions")
def transactions_page() -> str:
    search_query = request.args.get("q", default="").strip()
    return render_template(
        "transactions.html",
        **_transaction_form_context(
            "transactions",
            t("transactions_title"),
            t("transactions_subtitle"),
            search_query,
        ),
    )


@app.route("/transactions/add", methods=["POST"])
def add_transaction() -> str:
    category_id = request.form.get("category_id", type=int)
    amount = request.form.get("amount", type=float)
    note = request.form.get("note", default="").strip() or None
    date_value = _parse_datetime_local(request.form.get("date"))

    if category_id is None or amount is None or amount <= 0:
        flash(_flash_message("flash_amount_category_invalid"), "error")
        return redirect(url_for("transactions_page"))

    if not date_value:
        flash(_flash_message("flash_date_invalid"), "error")
        return redirect(url_for("transactions_page"))

    try:
        finance_manager.add_transaction(amount, category_id, note, date_value)
        _invalidate_summary_cache()
        flash(_flash_message("flash_transaction_added"), "success")
    except ValueError as exc:
        flash(str(exc), "error")

    return redirect(url_for("transactions_page"))


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
def edit_transaction(transaction_id: int) -> str:
    transaction_row = _find_transaction(transaction_id)
    if transaction_row is None:
        flash(_flash_message("flash_transaction_not_found"), "error")
        return redirect(url_for("transactions_page"))

    categories = db_helper.get_all_categories()

    if request.method == "POST":
        category_id = request.form.get("category_id", type=int)
        amount = request.form.get("amount", type=float)
        note = request.form.get("note", default="").strip() or None
        date_value = _parse_datetime_local(request.form.get("date"))

        if category_id is None or amount is None or amount <= 0 or not date_value:
            flash(_flash_message("flash_transaction_invalid"), "error")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        selected_category = next((item for item in categories if item["id"] == category_id), None)
        if selected_category is None:
            flash(_flash_message("flash_category_invalid"), "error")
            return redirect(url_for("edit_transaction", transaction_id=transaction_id))

        final_amount = abs(amount) if selected_category["type"] == 1 else -abs(amount)
        db_helper.update_transaction(
            transaction_id,
            date=date_value,
            amount=final_amount,
            category_id=category_id,
            note=note,
        )
        _invalidate_summary_cache()
        flash(_flash_message("flash_transaction_updated"), "success")
        return redirect(url_for("transactions_page"))

    return render_template(
        "transaction_edit.html",
        **_shared_context(
            "transactions",
            t("edit_transaction_title"),
            t("edit_transaction_subtitle"),
        ),
        transaction_row=transaction_row,
        categories=categories,
    )


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
def delete_transaction(transaction_id: int) -> str:
    if db_helper.delete_transaction(transaction_id):
        _invalidate_summary_cache()
        flash(_flash_message("flash_transaction_deleted"), "success")
    else:
        flash(_flash_message("flash_transaction_delete_failed"), "error")
    return redirect(url_for("transactions_page"))


@app.route("/categories")
def categories_page() -> str:
    return render_template(
        "categories.html",
        **_shared_context(
            "categories",
            t("categories_title"),
            t("categories_subtitle"),
        ),
    )


@app.route("/categories/add", methods=["POST"])
def add_category() -> str:
    category_name = request.form.get("category_name", default="").strip()
    category_type = request.form.get("category_type", type=int)

    if not category_name or category_type not in (0, 1):
        flash(_flash_message("flash_category_name_type_invalid"), "error")
        return redirect(url_for("categories_page"))

    category_key = request.form.get("key", default="").strip().lower() or _slugify(category_name)
    created_id = db_helper.create_category(category_key, category_name, category_type)

    if created_id is None:
        flash(_flash_message("flash_category_exists"), "error")
    else:
        flash(_flash_message("flash_category_created"), "success")

    return redirect(url_for("categories_page"))


@app.route("/categories/delete", methods=["POST"])
def delete_category() -> str:
    key = request.form.get("key", default="").strip()
    if not key:
        flash(_flash_message("flash_category_key_missing"), "error")
        return redirect(url_for("categories_page"))

    if db_helper.delete_category(key):
        flash(_flash_message("flash_category_deleted"), "success")
    else:
        flash(_flash_message("flash_category_delete_failed"), "error")

    return redirect(url_for("categories_page"))


@app.route("/budget")
def budget_page() -> str:
    return render_template(
        "budget.html",
        **_shared_context(
            "budget",
            t("budget_title"),
            t("budget_subtitle"),
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
    shared_context = _shared_context(
        "reports",
        t("reports_title"),
        t("reports_subtitle"),
    )

    excluded_note_pattern = "%chat-edit%"
    current_summary = db_helper.get_period_summary(start_date, end_date)
    visible_current_summary = db_helper.get_period_summary(start_date, end_date, excluded_note_pattern)

    previous_start_date, previous_end_date = _month_bounds(previous_year, previous_month)
    previous_summary = db_helper.get_period_summary(previous_start_date, previous_end_date)
    visible_previous_summary = db_helper.get_period_summary(previous_start_date, previous_end_date, excluded_note_pattern)

    total_income = current_summary["total_income"]
    total_expense = current_summary["total_expense"]
    net_balance = current_summary["net_balance"]

    previous_income = previous_summary["total_income"]
    previous_expense = previous_summary["total_expense"]
    previous_net_balance = previous_summary["net_balance"]

    def _delta_label(current_value: float, previous_value: float) -> tuple[str, str, float]:
        delta_value = current_value - previous_value
        if previous_value == 0:
            if current_value == 0:
                return t("unchanged"), t("flat"), 0
            return t("newly_emerged"), t("up"), 100
        return f"{abs(delta_value) / previous_value * 100:.1f}%", t("up") if delta_value >= 0 else t("down"), delta_value

    income_delta_text, income_delta_trend, income_delta_value = _delta_label(total_income, previous_income)
    expense_delta_text, expense_delta_trend, expense_delta_value = _delta_label(total_expense, previous_expense)
    balance_delta_text, balance_delta_trend, balance_delta_value = _delta_label(net_balance, previous_net_balance)
    count_delta_text, count_delta_trend, count_delta_value = _delta_label(
        visible_current_summary["transaction_count"],
        visible_previous_summary["transaction_count"],
    )

    daily_summary = db_helper.get_daily_summary(start_date, end_date)
    day_income = {row["day"]: float(row["income"] or 0) for row in daily_summary}
    day_expense = {row["day"]: float(row["expense"] or 0) for row in daily_summary}

    days_in_month = calendar.monthrange(year, month)[1]
    day_labels = [f"{day:02d}" for day in range(1, days_in_month + 1)]
    report_income_series = [day_income.get(f"{year:04d}-{month:02d}-{day:02d}", 0) for day in range(1, days_in_month + 1)]
    report_expense_series = [day_expense.get(f"{year:04d}-{month:02d}-{day:02d}", 0) for day in range(1, days_in_month + 1)]

    category_summary = db_helper.get_category_summary(start_date, end_date)
    category_values = [abs(float(item["total_amount"] or 0)) for item in category_summary]
    category_total = sum(category_values)
    category_percentages = [round((value / category_total) * 100, 1) if category_total else 0 for value in category_values]
    monthly_summary = _cached_monthly_summary()

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

    recent_page_data = db_helper.get_transactions_by_date_range_page(
        start_date,
        end_date,
        page=recent_page,
        per_page=recent_per_page,
        excluded_note_pattern=excluded_note_pattern,
    )
    recent_total_items = recent_page_data["total_items"]
    recent_total_pages = max(1, int(math.ceil(recent_total_items / recent_per_page))) if recent_per_page else 1
    if recent_page < 1:
        recent_page = 1
    if recent_page > recent_total_pages:
        recent_page = recent_total_pages

    if recent_page != request.args.get("recent_page", default=1, type=int) and recent_total_items:
        recent_page_data = db_helper.get_transactions_by_date_range_page(
            start_date,
            end_date,
            page=recent_page,
            per_page=recent_per_page,
            excluded_note_pattern=excluded_note_pattern,
        )

    recent_start_index = (recent_page - 1) * recent_per_page
    recent_end_index = recent_start_index + recent_per_page
    recent_report_transactions = recent_page_data["transactions"]

    recent_display_start = recent_start_index + 1 if recent_total_items else 0
    recent_display_end = min(recent_end_index, recent_total_items) if recent_total_items else 0

    comparison_chart_labels = [t("income"), t("expense"), t("report_balance_label")]
    comparison_current_values = [total_income, total_expense, net_balance]
    comparison_previous_values = [previous_income, previous_expense, previous_net_balance]

    return render_template(
        "reports.html",
        **shared_context,
        report_period_options=_build_report_period_options(),
        period=normalized_period,
        selected_period_label=_month_label(year, month),
        previous_period_label=_month_label(previous_year, previous_month),
        recent_report_transactions=recent_report_transactions,
        total_income=total_income,
        total_expense=total_expense,
        net_balance=net_balance,
        previous_income=previous_income,
        previous_expense=previous_expense,
        previous_net_balance=previous_net_balance,
        comparison_cards=[
            {
                "title": t("report_total_income"),
                "current": total_income,
                "previous": previous_income,
                "delta_text": income_delta_text,
                "delta_trend": income_delta_trend,
                "delta_value": income_delta_value,
            },
            {
                "title": t("report_total_expense"),
                "current": total_expense,
                "previous": previous_expense,
                "delta_text": expense_delta_text,
                "delta_trend": expense_delta_trend,
                "delta_value": expense_delta_value,
            },
            {
                "title": t("report_net_balance"),
                "current": net_balance,
                "previous": previous_net_balance,
                "delta_text": balance_delta_text,
                "delta_trend": balance_delta_trend,
                "delta_value": balance_delta_value,
            },
            {
                "title": t("report_transaction_count"),
                "current": visible_current_summary["transaction_count"],
                "previous": visible_previous_summary["transaction_count"],
                "delta_text": count_delta_text,
                "delta_trend": count_delta_trend,
                "delta_value": count_delta_value,
            },
        ],
        day_labels=day_labels,
        report_income_series=report_income_series,
        report_expense_series=report_expense_series,
        report_category_labels=[_category_label(str(item.get("category_key", "")), item["category_name"]) for item in category_summary],
        report_category_values=category_values,
        report_category_percentages=category_percentages,
        report_category_legend_labels=[
            f"{_category_label(str(item.get('category_key', '')), item['category_name'])} ({percent:.1f}%)" if category_total else _category_label(str(item.get('category_key', '')), item['category_name'])
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
    if budget_value is None or budget_value <= 0:
        flash(_flash_message("flash_budget_invalid"), "error")
        return redirect(url_for("budget_page"))

    db_helper.set_budget_limit(budget_value)
    _invalidate_summary_cache()
    flash(_flash_message("flash_budget_updated"), "success")
    return redirect(url_for("budget_page"))


@app.route("/reset", methods=["POST"])
def reset_database() -> str:
    db_helper.reset_database()
    app.config["DATABASE_READY"] = True
    _invalidate_summary_cache()
    flash(_flash_message("flash_database_reset"), "success")
    return redirect(url_for("dashboard"))


@app.route("/demo-data", methods=["POST"])
def create_demo_data() -> str:
    db_helper.reset_database()
    app.config["DATABASE_READY"] = True
    _invalidate_summary_cache()
    created, message = _seed_demo_transactions()
    flash(message if created else _flash_message("flash_demo_failed"), "success" if created else "error")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug_mode)