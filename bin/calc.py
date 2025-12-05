# bin/calc.py

def main(args, syscall):
    """Simple calculator: calc 1 + 2"""
    try:
        expr = " ".join(args)
        result = eval(expr)
        syscall.log(f"[calc] {expr} = {result}")
        return str(result)
    except Exception as e:
        return f"calc error: {e}"
# --- IGNORE ---