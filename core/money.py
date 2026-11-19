def format_rub(kop: int) -> str:
    sign = "−" if kop < 0 else ""
    rub, rest = divmod(abs(kop), 100)
    whole = f"{rub:,}".replace(",", " ")
    return f"{sign}{whole} ₽" if rest == 0 else f"{sign}{whole},{rest:02d} ₽"
