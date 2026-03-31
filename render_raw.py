#!/usr/bin/env python3
import re
import sys


class Terminal:
    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.buf  = [[" "] * cols for _ in range(rows)]
        self.attr = [[False] * cols for _ in range(rows)]  # True = reverse video
        self.r = 0
        self.c = 0
        self.alt     = False
        self.reverse = False
        self.line_map = {
            "l": "┌", "k": "┐", "m": "└", "j": "┘", "q": "─", "x": "│",
            "t": "├", "u": "┬", "v": "┴", "w": "┼", "n": "┤",
        }

    def ensure_pos(self, r, c):
        if r < 0: r = 0
        if c < 0: c = 0
        if r >= self.rows:
            for _ in range(r - self.rows + 1):
                self.buf.append([" "] * self.cols)
                self.attr.append([False] * self.cols)
            self.rows = len(self.buf)
        self.r = r
        self.c = min(c, self.cols - 1)

    def write_char(self, ch):
        if ch == "\n":
            self.r += 1
            self.c = 0
            if self.r >= self.rows:
                self.ensure_pos(self.r, self.c)
            return
        if ch == "\r":
            self.c = 0
            return
        out = ch
        if self.alt and ch in self.line_map:
            out = self.line_map[ch]
        if 0 <= self.r < self.rows and 0 <= self.c < self.cols:
            self.buf[self.r][self.c]  = out
            self.attr[self.r][self.c] = self.reverse
        self.c += 1
        if self.c >= self.cols:
            self.c = 0
            self.r += 1
            if self.r >= self.rows:
                self.ensure_pos(self.r, self.c)

    def clear_screen(self):
        for i in range(self.rows):
            for j in range(self.cols):
                self.buf[i][j]  = " "
                self.attr[i][j] = False
        self.r = 0
        self.c = 0

    def clear_eol(self):
        for j in range(self.c, self.cols):
            self.buf[self.r][j]  = " "
            self.attr[self.r][j] = False

    def set_attrs(self, parts):
        """Parse SGR params and update reverse state."""
        if not parts:
            self.reverse = False
            return
        for p in parts:
            n = int(p) if p else 0
            if n == 0:
                self.reverse = False
            elif n == 7:
                self.reverse = True
            elif n == 27:
                self.reverse = False
            # other attributes (bold, underline, etc.) ignored for now

    def render(self):
        """Plain text render (trailing spaces stripped). Reverse-video runs wrapped in [...]."""
        lines = []
        for r in range(self.rows):
            row_chars = self.buf[r]
            row_attr  = self.attr[r]
            # find last non-space
            last = -1
            for c in range(self.cols - 1, -1, -1):
                if row_chars[c] != " ":
                    last = c
                    break
            if last < 0:
                lines.append("")
                continue
            out = []
            in_rev = False
            for c in range(last + 1):
                ch = row_chars[c]
                rv = row_attr[c]
                if rv and not in_rev:
                    out.append("[")
                    in_rev = True
                elif not rv and in_rev:
                    out.append("]")
                    in_rev = False
                out.append(ch)
            if in_rev:
                out.append("]")
            lines.append("".join(out))
        # strip trailing empty lines
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"

    def render_spans(self):
        """
        Return list of rows; each row is a list of (text, reverse) span tuples.
        Used by the PNG renderer for styled output.
        """
        rows_out = []
        for r in range(self.rows):
            row_chars = self.buf[r]
            row_attr  = self.attr[r]
            # find last non-space
            last = -1
            for c in range(self.cols - 1, -1, -1):
                if row_chars[c] != " ":
                    last = c
                    break
            if last < 0:
                rows_out.append([("", False)])
                continue
            spans = []
            cur_text = []
            cur_rev  = row_attr[0]
            for c in range(last + 1):
                rv = row_attr[c]
                if rv != cur_rev:
                    spans.append(("".join(cur_text), cur_rev))
                    cur_text = []
                    cur_rev  = rv
                cur_text.append(row_chars[c])
            spans.append(("".join(cur_text), cur_rev))
            rows_out.append(spans)
        # strip trailing blank rows
        while rows_out and all(t == "" or t == " " * len(t) for t, _ in rows_out[-1]):
            rows_out.pop()
        return rows_out


def parse_raw(raw, rows=40, cols=80):
    t = Terminal(rows=rows, cols=cols)
    _feed(t, raw)
    return t.render()


def parse_raw_spans(raw, rows=40, cols=80):
    """Like parse_raw but returns styled span data for PNG rendering."""
    t = Terminal(rows=rows, cols=cols)
    _feed(t, raw)
    return t.render_spans()


def _feed(t, raw):
    i = 0
    L = len(raw)
    while i < L:
        ch = raw[i]
        if ch == "\x1b":
            i += 1
            if i >= L:
                break
            nxt = raw[i]
            if nxt == "[":
                i += 1
                params = ""
                while i < L and not (64 <= ord(raw[i]) <= 126):
                    params += raw[i]
                    i += 1
                if i >= L:
                    break
                final = raw[i]
                i += 1
                parts = [p for p in params.split(";") if p != ""]
                if final in ("H", "f"):
                    if len(parts) >= 2:
                        t.ensure_pos(int(parts[0]) - 1, int(parts[1]) - 1)
                    elif len(parts) == 1:
                        t.ensure_pos(int(parts[0]) - 1, 0)
                    else:
                        t.ensure_pos(0, 0)
                elif final == "J":
                    t.clear_screen()
                elif final == "C":
                    n = int(parts[0]) if parts else 1
                    t.ensure_pos(t.r, t.c + n)
                elif final == "K":
                    t.clear_eol()
                elif final == "m":
                    t.set_attrs(parts)
                continue
            if nxt == "(":
                i += 1
                if i >= L:
                    break
                ch2 = raw[i]
                i += 1
                t.alt = (ch2 == "0")
                continue
            i += 1
            continue
        else:
            t.write_char(ch)
            i += 1
