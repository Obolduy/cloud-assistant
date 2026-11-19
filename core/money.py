def format_rub(kop: int) -> str:
    sign = "−" if kop < 0 else ""
    rub, rest = divmod(abs(kop), 100)
    whole = f"{rub:,}".replace(",", " ")
    return f"{sign}{whole} ₽" if rest == 0 else f"{sign}{whole},{rest:02d} ₽"


def with_rub(value):
    if isinstance(value, list):
        return [with_rub(v) for v in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        out[key] = with_rub(item)
        if key.endswith("_kop") and isinstance(item, int):
            out[key.removesuffix("_kop") + "_rub"] = format_rub(item)
    return out
