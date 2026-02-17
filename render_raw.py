#!/usr/bin/env python3
import re
import sys


class Terminal:
    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.buf = [[" "] * cols for _ in range(rows)]
        self.r = 0
        self.c = 0
        self.alt = False
        self.line_map = {
            "l": "┌", "k": "┐", "m": "└", "j": "┘", "q": "─", "x": "│",
            "t": "├", "u": "┬", "v": "┴", "w": "┼", "n": "┤",
        }

    def ensure_pos(self, r, c):
        if r < 0:
            r = 0
        if c < 0:
            c = 0
        if r >= self.rows:
            # grow rows
            for _ in range(r - self.rows + 1):
                self.buf.append([" "] * self.cols)
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
            self.buf[self.r][self.c] = out
        self.c += 1
        if self.c >= self.cols:
            self.c = 0
            self.r += 1
            if self.r >= self.rows:
                self.ensure_pos(self.r, self.c)

    def clear_screen(self):
        for i in range(self.rows):
            for j in range(self.cols):
                self.buf[i][j] = " "
        self.r = 0
        self.c = 0

    def clear_eol(self):
        for j in range(self.c, self.cols):
            self.buf[self.r][j] = " "

    def render(self):
        # return string with trimmed trailing spaces
        return "\n".join(("".join(row).rstrip() for row in self.buf)).rstrip() + "\n"


def parse_raw(raw, rows=40, cols=80):
    t = Terminal(rows=rows, cols=cols)
    i = 0
    L = len(raw)
    while i < L:
        ch = raw[i]
        if ch == "\x1b":
            i += 1
            if i >= L:
                break
            nxt = raw[i]
            # CSI
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
                        r = int(parts[0]) - 1
                        c = int(parts[1]) - 1
                        t.ensure_pos(r, c)
                    elif len(parts) == 1:
                        r = int(parts[0]) - 1
                        t.ensure_pos(r, 0)
                    else:
                        t.ensure_pos(0, 0)
                elif final == "J":
                    # clear screen
                    t.clear_screen()
                elif final == "C":
                    n = int(parts[0]) if parts else 1
                    t.ensure_pos(t.r, t.c + n)
                elif final == "K":
                    t.clear_eol()
                elif final == "m":
                    # ignore attributes
                    pass
                else:
                    # ignore other CSI sequences
                    pass
                continue
            # charset selects like ESC ( 0 or ESC ( B
            if nxt == "(":
                i += 1
                if i >= L:
                    break
                ch2 = raw[i]
                i += 1
                if ch2 == "0":
                    t.alt = True
                elif ch2 == "B":
                    t.alt = False
                else:
                    t.alt = False
                continue
            # other two-byte sequences
            i += 1
            continue
        else:
            t.write_char(ch)
            i += 1
    return t.render()