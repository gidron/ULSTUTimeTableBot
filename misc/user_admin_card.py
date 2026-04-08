def format_user_admin_card_html(
    *,
    title: str,
    tg_id: int,
    full_name: str | None,
    username: str | None,
    group_name: str | None = None,
) -> str:
    """Тот же набор полей, что в уведомлении о новом пользователе (+ группа, если есть)."""
    user_line = f"@{username}" if username else "—"
    lines = [
        f"<b>{title}</b>",
        f"ID: <code>{tg_id}</code>",
        f"Full name: {full_name or '—'}",
        f"username: {user_line}",
    ]
    if group_name:
        lines.append(f"Группа: <b>{group_name}</b>")
    return "\n".join(lines)
