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
    """RPNの評価手順を 1.右Pop ➔ 2.左Pop ➔ 3.演算実行 ➔ 4.結果Push に細分化"""
    stack = []
    steps = []

    steps.append({
        "type": "init", "token": "", "stack": [str(x) for x in stack], "calc_stage": None,
        "desc": "RPN式の計算評価を開始します。"
    })

    for token in rpn_tokens:
        if token.isalnum():
            val = var_values.get(token, None)
            if val is None:
                try:
                    val = float(token) if '.' in token else int(token)
                except ValueError:
                    val = 1

            stack.append(val)
            steps.append({
                "type": "push_val", "token": str(val), "stack": [str(x) for x in stack], "calc_stage": None,
                "desc": f"値/変数 '{token}' (= {val}) をスタックに Push"
            })
        elif token in PRECEDENCE:
            if len(stack) >= 2:
                # 1. 右オペランド(Pop 1回目)
                b = stack.pop()
                steps.append({
                    "type": "pop_b", "token": token, "stack": [str(x) for x in stack],
                    "calc_stage": {"left": "?", "op": token, "right": str(b), "res": None},
                    "desc": f"演算子 '{token}' を検出 ➔ スタックから右項 B = {b} を Pop"
                })

                # 2. 左オペランド(Pop 2回目)
                a = stack.pop()
                steps.append({
                    "type": "pop_a", "token": token, "stack": [str(x) for x in stack],
                    "calc_stage": {"left": str(a), "op": token, "right": str(b), "res": None},
                    "desc": f"スタックから左項 A = {a} を Pop ➔ 式 '{a} {token} {b}' が展開されました"
                })

                # 3. 演算の計算実行
                res = 0
                if token == '+': res = a + b
                elif token == '-': res = a - b
                elif token == '*': res = a * b
                elif token == '/': res = a / b if b != 0 else 0
                elif token == '^': res = a ** b

                if isinstance(res, float) and res.is_integer():
                    res = int(res)

                steps.append({
                    "type": "calc_eval", "token": token, "stack": [str(x) for x in stack],
                    "calc_stage": {"left": str(a), "op": token, "right": str(b), "res": str(res)},
                    "desc": f"計算を実行: {a} {token} {b} = {res}"
                })

                # 4. 結果の Push
                stack.append(res)
                steps.append({
                    "type": "push_res", "token": str(res), "stack": [str(x) for x in stack],
                    "calc_stage": {"left": str(a), "op": token, "right": str(b), "res": str(res)},
                    "desc": f"計算結果 '{res}' をスタックに Push"
                })

    final_result = stack[-1] if stack else 0
    steps.append({
        "type": "finish", "token": "=", "stack": [str(x) for x in stack], "calc_stage": None,
        "desc": f"すべての計算が完了しました！ 最終解 = {final_result}"
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
    app.run(debug=True)