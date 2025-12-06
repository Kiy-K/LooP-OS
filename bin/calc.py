# bin/calc.py
import json

def main(args, sys):
    """
    Simple Calculator App for Agent.
    Usage: run calc <expression>
    Returns: JSON {"result": value, "error": msg}
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
