from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

PRECEDENCE = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}

def tokenize(expr):
    pattern = r'\d+\.\d+|\d+|[A-Za-z]+|[\+\-\*\/\^\(\)]'
    return re.findall(pattern, expr)

def infix_to_rpn_steps(expr):
    tokens = tokenize(expr)
    stack = []
    output = []
    steps = []

    steps.append({
        "type": "init", "token": "", "stack": list(stack), "output": list(output),
        "desc": "中置記法から逆ポーランド記法(RPN)への変換を開始します。"
    })

    for token in tokens:
        if token.isalnum():
            output.append(token)
            steps.append({
                "type": "operand", "token": token, "stack": list(stack), "output": list(output),
                "desc": f"値・変数 '{token}' を出力に追加"
            })
        elif token == '(':
            stack.append(token)
            steps.append({
                "type": "push", "token": token, "stack": list(stack), "output": list(output),
                "desc": "左括弧 '(' をスタックに Push"
            })
        elif token == ')':
            steps.append({
                "type": "read", "token": token, "stack": list(stack), "output": list(output),
                "desc": "右括弧 ')' を検出。'(' まで Pop します。"
            })
            while stack and stack[-1] != '(':
                popped = stack.pop()
                output.append(popped)
                steps.append({
                    "type": "pop", "token": popped, "stack": list(stack), "output": list(output),
                    "desc": f"スタックから '{popped}' を Pop して出力に追加"
                })
            if stack and stack[-1] == '(':
                stack.pop()
                steps.append({
                    "type": "pop_discard", "token": "(", "stack": list(stack), "output": list(output),
                    "desc": "対応する '(' をスタックから破棄"
                })
        else:
            while (stack and stack[-1] != '(' and
                   PRECEDENCE.get(stack[-1], 0) >= PRECEDENCE.get(token, 0)):
                popped = stack.pop()
                output.append(popped)
                steps.append({
                    "type": "pop", "token": popped, "stack": list(stack), "output": list(output),
                    "desc": f"優先度比較: '{popped}' >= '{token}' のため '{popped}' を Pop して出力に追加"
                })
            stack.append(token)
            steps.append({
                "type": "push", "token": token, "stack": list(stack), "output": list(output),
                "desc": f"演算子 '{token}' をスタックに Push"
            })

    while stack:
        popped = stack.pop()
        output.append(popped)
        steps.append({
            "type": "pop", "token": popped, "stack": list(stack), "output": list(output),
            "desc": f"残った演算子 '{popped}' を Pop して出力に追加"
        })

    return steps

def rpn_to_infix_steps(expr):
    tokens = tokenize(expr)
    stack = []
    steps = []

    steps.append({
        "type": "init", "token": "", "stack": list(stack), "output": [],
        "desc": "RPNから中置記法への変換を開始します。"
    })

    for token in tokens:
        if token.isalnum():
            stack.append(token)
            steps.append({
                "type": "push", "token": token, "stack": list(stack), "output": list(stack),
                "desc": f"値・変数 '{token}' をスタックに Push"
            })
        else:
            if len(stack) >= 2:
                right = stack.pop()
                left = stack.pop()
                new_expr = f"({left} {token} {right})"
                stack.append(new_expr)
                steps.append({
                    "type": "pop_combine", "token": token, "stack": list(stack), "output": list(stack),
                    "desc": f"'{left}' と '{right}' を Pop し、'{token}' で結合: '{new_expr}'"
                })

    return steps

def evaluate_rpn_steps(rpn_tokens, var_values):
    """RPNのトークン列から実際にスタックを使って計算を実行する"""
    stack = []
    steps = []

    steps.append({
        "type": "init", "token": "", "stack": [str(x) for x in stack], "output": [],
        "desc": "RPN式の計算評価を開始します。"
    })

    for token in rpn_tokens:
        # 数値または変数
        if token.isalnum():
            val = var_values.get(token, None)
            if val is None:
                try:
                    val = float(token) if '.' in token else int(token)
                except ValueError:
                    val = 1  # デフォルト値

            stack.append(val)
            steps.append({
                "type": "push_val", "token": str(val), "stack": [str(x) for x in stack], "output": [],
                "desc": f"値/変数 '{token}' (= {val}) をスタックに Push"
            })
        elif token in PRECEDENCE:
            if len(stack) >= 2:
                b = stack.pop()
                a = stack.pop()
                res = 0
                if token == '+': res = a + b
                elif token == '-': res = a - b
                elif token == '*': res = a * b
                elif token == '/': res = a / b if b != 0 else 0
                elif token == '^': res = a ** b

                if isinstance(res, float) and res.is_integer():
                    res = int(res)

                stack.append(res)
                steps.append({
                    "type": "calc", "token": token, "stack": [str(x) for x in stack], "output": [f"計算結果: {res}"],
                    "desc": f"Pop: {a} と {b} ➔ 計算 ({a} {token} {b}) = {res} ➔ 結果 {res} を Push"
                })

    final_result = stack[-1] if stack else 0
    steps.append({
        "type": "finish", "token": "=", "stack": [str(x) for x in stack], "output": [f"最終結果: {final_result}"],
        "desc": f"計算完了！ 最終解 = {final_result}"
    })
    return steps

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    expr = data.get('expression', '')
    mode = data.get('mode', 'infix_to_rpn')

    if mode == 'infix_to_rpn':
        steps = infix_to_rpn_steps(expr)
    else:
        steps = rpn_to_infix_steps(expr)

    return jsonify({"steps": steps})

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    rpn_tokens = data.get('rpn_tokens', [])
    var_values = data.get('var_values', {})
    steps = evaluate_rpn_steps(rpn_tokens, var_values)
    return jsonify({"steps": steps})

if __name__ == '__main__':
    app.run(debug=False)