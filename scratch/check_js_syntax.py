from pathlib import Path

js_files = list(Path("static/js").glob("*.js"))

for f in js_files:
    content = f.read_text(encoding="utf-8")
    # Check basic bracket / parenthesis balancing
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    in_string = False
    str_char = None
    in_line_comment = False
    in_block_comment = False
    escaped = False
    line_no = 1
    col_no = 0
    error = None

    i = 0
    while i < len(content):
        c = content[i]
        col_no += 1
        if c == '\n':
            line_no += 1
            col_no = 0
            in_line_comment = False

        if in_line_comment:
            i += 1
            continue

        if in_block_comment:
            if c == '*' and i + 1 < len(content) and content[i + 1] == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_string:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == str_char:
                in_string = False
                str_char = None
            i += 1
            continue

        # Check comment start
        if c == '/' and i + 1 < len(content):
            if content[i + 1] == '/':
                in_line_comment = True
                i += 2
                continue
            elif content[i + 1] == '*':
                in_block_comment = True
                i += 2
                continue

        # Check string start
        if c in ("'", '"', '`'):
            in_string = True
            str_char = c
            i += 1
            continue

        if c in ('(', '{', '['):
            stack.append((c, line_no, col_no))
        elif c in (')', '}', ']'):
            expected = pairs[c]
            if not stack or stack[-1][0] != expected:
                error = f"Unmatched '{c}' at line {line_no}, col {col_no} (expected {expected})"
                break
            stack.pop()

        i += 1

    if stack and not error:
        error = f"Unclosed {stack[-1][0]} from line {stack[-1][1]}, col {stack[-1][2]}"

    if error:
        print(f"FAILED {f.name}: {error}")
    else:
        print(f"PASSED {f.name}: clean balance")
