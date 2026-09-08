#!/usr/bin/env python3
"""Xuyiming：改编自 BaiTu-iOS xcindent 的词法缩进器，来源与许可见 NOTICE.md。"""
import re
import sys

KEYWORD_COLON = re.compile(r'^([A-Za-z_]\w*)\s*:(?!:)')  # ObjC 关键字参数续行；排除 ::（C++ 作用域）


class Frame:
    """一个未闭合的定界上下文。kind ∈ {'brace','paren','bracket'}。"""
    __slots__ = ('kind', 'opener_indent', 'after_open_col', 'is_message',
                 'first_colon_col', 'is_switch')

    def __init__(self, kind, opener_indent, after_open_col):
        self.kind = kind
        self.opener_indent = opener_indent      # 开启该定界符那一行的行缩进
        self.after_open_col = after_open_col     # 开启符后紧跟内容的列（无内容则 None）
        self.is_message = False                  # bracket 专用：是否为 ObjC 消息（出现过 keyword:）
        self.first_colon_col = None              # 消息首个冒号所在列
        self.is_switch = False                   # brace 专用：是否为 switch 块（出现过 case/default）


class Lexer:
    """跨行维护 字符串/字符/行注释/块注释 状态，逐行喂入，产出结构化 token 供缩进器消费。"""

    def __init__(self):
        self.in_block_comment = False
        self.block_comment_col = None   # 当前未闭合块注释 /* 的列（输出坐标）

    def line_starts_in_comment(self):
        return self.in_block_comment

    def scan(self, line):
        """扫描一行，返回 (events, ended_with_backslash)。
        events: 有序的 ('open'|'close'|'colon'|'preproc', char, col) —— 已跳过字符串/注释内的定界符。"""
        events = []
        i, n = 0, len(line)
        # 行注释/块注释状态在行内推进；块注释跨行由 self.in_block_comment 持有
        while i < n:
            c = line[i]
            if self.in_block_comment:
                if c == '*' and i + 1 < n and line[i + 1] == '/':
                    self.in_block_comment = False
                    self.block_comment_col = None
                    i += 2
                    continue
                i += 1
                continue
            if c == '/' and i + 1 < n and line[i + 1] == '/':
                break  # 行注释，其后忽略
            if c == '/' and i + 1 < n and line[i + 1] == '*':
                self.in_block_comment = True
                self.block_comment_col = i   # 记录 /* 列，供续行对齐到 col+1
                i += 2
                continue
            if c == '"' or c == "'":
                i = self._skip_string(line, i, c)
                continue
            if c in '{([':
                events.append(('open', c, i))
            elif c in '})]':
                events.append(('close', c, i))
            elif c == ':':
                events.append(('colon', c, i))
            i += 1
        ended_bs = (not self.in_block_comment) and line.rstrip('\n').endswith('\\')
        return events, ended_bs

    @staticmethod
    def _skip_string(line, i, quote):
        n = len(line)
        i += 1
        while i < n:
            if line[i] == '\\':
                i += 2
                continue
            if line[i] == quote:
                return i + 1
            i += 1
        return i  # 未闭合（跨行字符串少见），停在行尾


class Reindenter:
    def __init__(self, width=4, indent_case=True, indent_preproc=False):
        self.W = width
        self.indent_case = indent_case
        self.indent_preproc = indent_preproc

    def reindent(self, text, ranges=None):
        """ranges=None 全文件重缩进；否则仅重写落在 [(start,end),...]（1-based 闭区间）内的行，
        其余行原样保留。状态跟踪对未改动行用其真实列坐标 → 改动行冒号对齐到周围既有代码的实际列。"""
        lex = Lexer()
        stack = []          # 未闭合定界符栈（brace/paren/bracket，含顺序）
        out = []
        cont_from_backslash = False
        in_preproc = False              # 预处理指令内（含 \ 续行）
        prev_backslash = False          # 上一预处理行是否以 \ 续行
        method = {'active': False, 'colon': None}  # ObjC 方法签名冒号对齐上下文

        for lineno, raw in enumerate(text.split('\n'), start=1):
            raw = raw.rstrip('\n')
            content = raw.strip()
            apply_ln = ranges is None or self._in_ranges(lineno, ranges)
            starts_in_comment = lex.line_starts_in_comment()

            if content == '':
                out.append('' if apply_ln else raw)
                lex.scan(raw)   # 空行也要推进注释状态
                continue

            if starts_in_comment:
                # 块注释续行：对齐到 /* 列 + 1（与 Xcode 一致，非保留原样）
                col = lex.block_comment_col
                ind = (col + 1) if col is not None else 0
                emit = (' ' * ind + content) if apply_ln else raw
                out.append(emit)
                lex.scan(emit)
                continue

            # 预处理指令（# 开头 或 上一预处理行以 \ 续行）：Xcode 默认顶格，且宏内花括号不算真实作用域
            if content[0] == '#' or (in_preproc and prev_backslash):
                ind = self._brace_depth(stack) * self.W if self.indent_preproc else 0
                emit = (' ' * ind + content) if apply_ln else raw
                out.append(emit)
                lex.scan(emit)                       # 仅推进注释/字符串状态，丢弃定界符事件
                in_preproc = True
                prev_backslash = content.rstrip().endswith('\\')
                if not prev_backslash:
                    in_preproc = False
                cont_from_backslash = False
                continue
            in_preproc = False

            # 方法签名起始：语句层的 - / + 方法声明/定义
            if not method['active'] and self._inner_brace(stack) is None and re.match(r'^[-+]\s*\(', content):
                method['active'] = True
                method['colon'] = None

            if apply_ln:
                indent = self._indent_for(content, stack, cont_from_backslash, method)
                emit = ' ' * indent + content
            else:
                emit = raw
                indent = len(raw) - len(raw.lstrip())
            out.append(emit)

            events, ended_bs = lex.scan(emit)
            self._apply_events(events, stack, indent, emit)
            cont_from_backslash = ended_bs

            # 方法签名：捕获首个选择器冒号列；遇 { 体或 ; 声明结束则退出
            if method['active']:
                if method['colon'] is None:
                    fc = next((c for k, ch, c in events if k == 'colon'), None)
                    if fc is not None:
                        method['colon'] = fc
                if any(k == 'open' and ch == '{' for k, ch, c in events) or content.rstrip().endswith(';'):
                    method['active'] = False
                    method['colon'] = None

        return '\n'.join(out)

    @staticmethod
    def _in_ranges(lineno, ranges):
        for start, end in ranges:
            if start <= lineno <= end:
                return True
        return False

    # ---- 缩进决策 ----
    def _brace_depth(self, stack):
        return sum(1 for f in stack if f.kind == 'brace')

    def _indent_for(self, content, stack, cont_bs, method):
        fc = content[0]
        top = stack[-1] if stack else None

        # 行首闭合符：回退到对应开启符所在层
        if fc in '})]':
            for f in reversed(stack):
                if (f.kind, fc) in (('brace', '}'), ('paren', ')'), ('bracket', ']')):
                    if f.kind == 'brace':
                        return (self._brace_depth(stack) - 1) * self.W
                    return f.opener_indent
            return 0

        # 方法签名续行：keyword: 对齐到首个选择器冒号列
        if method['active'] and method['colon'] is not None:
            m = KEYWORD_COLON.match(content)
            if m:
                return max(0, method['colon'] - len(m.group(1)))

        # 花括号开头行（{ 或 @{）：始终走 brace 深度规则（优先于 bracket/paren 续行；
        # 这正是 Xcode 对 @[ 里嵌 @{ 的处理——brace 元素走深度、非 brace 元素走 bracket 续行）
        if fc == '{' or content.startswith('@{'):
            return self._brace_depth(stack) * self.W

        # goto 标签：语句层的 identifier: → 顶格（与 Xcode 一致）
        if (top is None or top.kind == 'brace') \
                and re.match(r'^[A-Za-z_]\w*\s*:(?!:)', content) \
                and not re.match(r'^(case\b|default\b)', content):
            return 0

        # 最内层是 ObjC 消息 → keyword: 续行冒号对齐
        if top and top.kind == 'bracket' and top.is_message:
            m = KEYWORD_COLON.match(content)
            if m and top.first_colon_col is not None:
                return max(0, top.first_colon_col - len(m.group(1)))
            if top.after_open_col is not None:
                return top.after_open_col
            return top.opener_indent + self.W

        # 最内层是非消息 bracket（@[ 数组字面量 / 消息链续行）：开启符后有内容则对齐之
        # （消息链 [[[a b]…] 对齐到接收者列），否则相对开启行 +W（@[ 换行数组元素）
        if top and top.kind == 'bracket':
            if top.after_open_col is not None:
                return top.after_open_col
            return top.opener_indent + self.W

        # 最内层是括号：有内容跟随则对齐开启符后，否则 +1 级
        if top and top.kind == 'paren':
            if top.after_open_col is not None:
                return top.after_open_col
            return top.opener_indent + self.W

        base = self._brace_depth(stack) * self.W
        bf = self._inner_brace(stack)

        # case/default 标签：停在 switch 花括号层；并把该 brace 标记为 switch
        if re.match(r'^(case\b|default\b\s*:)', content):
            if bf is not None:
                bf.is_switch = True
            return base

        # switch 直接子语句（非标签）：相对 case 标签再 +W（与 Xcode 一致）
        if self.indent_case and bf is not None and bf.is_switch:
            base += self.W
        if cont_bs:
            base += self.W
        return base

    @staticmethod
    def _inner_brace(stack):
        for f in reversed(stack):
            if f.kind == 'brace':
                return f
        return None

    # ---- 状态推进 ----
    def _apply_events(self, events, stack, line_indent, line):
        for kind, ch, col in events:
            if kind == 'open':
                fk = {'{': 'brace', '(': 'paren', '[': 'bracket'}[ch]
                # 开启符后同行有非空白内容 → 记录其列供续行对齐；否则 None（续行走 +W）
                rest = line[col + 1:]
                after = (col + 1 + (len(rest) - len(rest.lstrip()))) if rest.strip() else None
                f = Frame(fk, line_indent, after)
                stack.append(f)
            elif kind == 'close':
                want = {'}': 'brace', ')': 'paren', ']': 'bracket'}[ch]
                # 弹到匹配的定界符
                while stack and stack[-1].kind != want:
                    stack.pop()
                if stack:
                    stack.pop()
            elif kind == 'colon':
                # 记录最内层 bracket 的首个冒号列 → 标记为消息
                for f in reversed(stack):
                    if f.kind == 'bracket':
                        if f.first_colon_col is None:
                            f.first_colon_col = col
                            f.is_message = True
                        break
                    if f.kind in ('brace', 'paren'):
                        break  # 冒号不属于最内层消息


def main():
    import argparse
    import difflib
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Xuyiming：保守的 ObjC 词法缩进预览，不保证与 Xcode 完全等价")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--lines", action="append", default=[])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        raw_path = args.repo.resolve(strict=True) / args.file
        path = raw_path.resolve(strict=True)
        path.relative_to(args.repo.resolve(strict=True))
        if raw_path.is_symlink() or path.suffix not in (".h", ".m") or not 1 <= args.width <= 16:
            raise ValueError("仅支持项目内 .h/.m，缩进宽度 1–16；ObjC++ 请用 clang-format")
        original = path.read_bytes()
        text = original.decode("utf-8")
        # 词法器不能完整识别跨行字面量和宏续行；整文件拒绝比改坏运行时文本更安全。
        if "\\\n" in text or "\\\r\n" in text or 'R"' in text or '"""' in text:
            raise ValueError("包含跨行字符串、原始字符串或续行宏，请使用项目 clang-format")
        ranges = []
        for raw in args.lines:
            start, end = map(int, raw.split(":"))
            if start < 1 or end < start:
                raise ValueError("行区间必须是正向的 start:end")
            ranges.append((start, end))
        result = Reindenter(args.width).reindent(text, ranges or None)
        diff = "".join(difflib.unified_diff(text.splitlines(True), result.splitlines(True), fromfile=str(path), tofile=str(path)))
        if args.write and diff:
            if path.is_symlink() or path.read_bytes() != original:
                raise ValueError("预览期间源文件发生变化")
            path.write_bytes(result.encode("utf-8"))
        sys.stdout.write(diff)
        return 0 if args.write or not diff else 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
