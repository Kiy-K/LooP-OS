# bin/calc.py
"""
Calculator Application.

A simple, safe calculator utility designed for the Agent.
It evaluates mathematical expressions using a restricted environment.
"""

import json

def main(args, sys):
    """
    Calculator entry point.

    Evaluates a mathematical expression passed as arguments.

    Args:
        args (list): The expression to evaluate (e.g., ["2", "+", "2"]).
        sys (SyscallHandler): System interface (unused here).

    Returns:
        str: JSON string containing "result" or "error".
    """
    if not args:
        return json.dumps({"error": "Usage: calc <expression>"})

    expression = " ".join(args)

    # Safe evaluation of math expressions
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum
    }

    try:
        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})
