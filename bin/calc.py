# bin/calc.py

def main(args, syscall):
    """
    Simple Calculator App.
    Usage: calc <op> <a> <b>
    """
    if len(args) != 3:
        return "Usage: calc <op> <a> <b>\nOps: + - * /"

    op = args[0]
    try:
        a = float(args[1])
        b = float(args[2])
    except ValueError:
        return "Error: arguments must be numbers"

    if op == "+":
        res = a + b
    elif op == "-":
        res = a - b
    elif op == "*":
        res = a * b
    elif op == "/":
        if b == 0: return "Error: Division by zero"
        res = a / b
    else:
        return f"Unknown operator: {op}"

    result_str = f"{a} {op} {b} = {res}"

    # Optionally log to a file
    # syscall.sys_append("/var/log/calc.log", result_str)

    return result_str
