# bin/echo.py

def main(args, syscall):
    """Echo arguments back."""
    text = " ".join(args)
    syscall.log(f"[echo] {text}")
    return text
# --- IGNORE ---