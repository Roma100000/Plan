from datetime import datetime

def is_valid_deadline(deadline_str: str) -> bool:
    if not deadline_str:
        return True
    try:
        dt = datetime.strptime(deadline_str, "%d.%m.%Y").date()
        return dt >= datetime.now().date()
    except ValueError:
        return False