from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

# 演算子の優先順位
PRECEDENCE = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}

def tokenize(expr):
    """数式をトークン（数値・変数・演算子・括弧）のリストに分割"""
    pattern = r'\d+\.\d+|\d+|[A-Za-z]+|[\+\-\*\/\^\(\)]'
    return re.findall(pattern, expr)

def infix_to_rpn_steps(expr):
    tokens = tokenize(expr)
    stack = []
    output = []
    steps = []

    steps.append({
        "type": "init",
        "token": "",
        "stack": list(stack),
        "output": list(output),
        "desc": "変換を開始します。"
    })

    for token in tokens:
        if token.isalnum():
            output.append(token)
            steps.append({
                "type": "operand",
                "token": token,
                "stack": list(stack),
                "output": list(output),
                "desc": f"値 '{token}' をそのまま出力に追加"
            })
        elif token == '(':
            stack.append(token)
            steps.append({
                "type": "push",
                "token": token,
                "stack": list(stack),
                "output": list(output),
                "desc": f"左括弧 '(' をスタックに push"
            })
        elif token == ')':
            steps.append({
                "type": "read",
                "token": token,
                "stack": list(stack),
                "output": list(output),
                "desc": f"右括弧 ')' を検出。'(' が出るまでスタックから pop"
            })
            while stack and stack[-1] != '(':
                popped = stack.pop()
                output.append(popped)
                steps.append({
                    "type": "pop",
                    "token": popped,
                    "stack": list(stack),
                    "output": list(output),
                    "desc": f"スタックから '{popped}' を pop して出力に追加"
                })
            if stack and stack[-1] == '(':
                stack.pop() # '(' を破棄
                steps.append({
                    "type": "pop_discard",
                    "token": "(",
                    "stack": list(stack),
                    "output": list(output),
                    "desc": "対応する '(' をスタックから破棄"
                })
        else: # 演算子
            while (stack and stack[-1] != '(' and
                   PRECEDENCE.get(stack[-1], 0) >= PRECEDENCE.get(token, 0)):
                popped = stack.pop()
                output.append(popped)
                steps.append({
                    "type": "pop",
                    "token": popped,
                    "stack": list(stack),
                    "output": list(output),
                    "desc": f"優先度比較: '{popped}' >= '{token}' のため pop して出力に追加"
                })
            stack.append(token)
            steps.append({
                "type": "push",
                "token": token,
                "stack": list(stack),
                "output": list(output),
                "desc": f"演算子 '{token}' をスタックに push"
            })

    while stack:
        popped = stack.pop()
        output.append(popped)
        steps.append({
            "type": "pop",
            "token": popped,
            "stack": list(stack),
            "output": list(output),
            "desc": f"残った演算子 '{popped}' を pop して出力に追加"
        })

    return steps

def rpn_to_infix_steps(expr):
    tokens = tokenize(expr)
    stack = []
    steps = []

    steps.append({
        "type": "init",
        "token": "",
        "stack": list(stack),
        "output": [],
        "desc": "RPNから中置記法への変換を開始します。"
    })

    for token in tokens:
        if token.isalnum():
            stack.append(token)
            steps.append({
                "type": "push",
                "token": token,
                "stack": list(stack),
                "output": list(stack),
                "desc": f"値 '{token}' をスタックに push"
            })
        else:
            if len(stack) >= 2:
                right = stack.pop()
                left = stack.pop()
                new_expr = f"({left} {token} {right})"
                stack.append(new_expr)
                steps.append({
                    "type": "pop_combine",
                    "token": token,
                    "stack": list(stack),
                    "output": list(stack),
                    "desc": f"'{left}' と '{right}' を pop し、演算子 '{token}' で結合: '{new_expr}'"
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

if __name__ == '__main__':
    app.run(debug=False)