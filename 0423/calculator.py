import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


def _add_thousands_commas(int_part: str) -> str:
    if not int_part or int_part == '-':
        return int_part
    neg = int_part.startswith('-')
    digits = int_part[1:] if neg else int_part
    digits = digits.lstrip('0') or '0'
    out = []
    for i, ch in enumerate(reversed(digits)):
        if i and i % 3 == 0:
            out.append(',')
        out.append(ch)
    body = ''.join(reversed(out))
    return f'-{body}' if neg else body


def format_display(raw: str) -> str:
    if raw in ('', '-'):
        return '0' if raw == '' else '-0'
    if raw == '-.':
        return '-0.'
    if raw.endswith('.'):
        base = raw[:-1]
        if base == '':
            return '0.'
        if base == '-':
            return '-0.'
        ip = _add_thousands_commas(base)
        return f'{ip}.'
    if '.' in raw:
        ip, fp = raw.split('.', 1)
        if ip in ('', '-'):
            ip_fmt = '0' if ip == '' else '-0'
        else:
            ip_fmt = _add_thousands_commas(ip)
        return f'{ip_fmt}.{fp}'
    return _add_thousands_commas(raw)


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Calculator')
        self._entry = '0'
        self._stored = None
        self._pending_op = None
        self._fresh = True

        self._display = QLabel('0')
        self._display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._display.setMinimumHeight(96)
        self._display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        font = QFont('Segoe UI', 36)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self._display.setFont(font)
        self._display.setStyleSheet(
            'QLabel { background-color: #000000; color: #ffffff; padding: 12px 16px; }'
        )

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.addWidget(self._display, 0, 0, 1, 4)

        self._btn_style_gray = (
            'QPushButton { background-color: #a6a6a6; color: #000000; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #d0d0d0; }'
        )
        self._btn_style_dark = (
            'QPushButton { background-color: #333333; color: #ffffff; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #5a5a5a; }'
        )
        self._btn_style_orange = (
            'QPushButton { background-color: #ff9500; color: #ffffff; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #e68600; }'
        )

        row = 1
        for label, col, style in [
            ('AC', 0, self._btn_style_gray),
            ('+/-', 1, self._btn_style_gray),
            ('%', 2, self._btn_style_gray),
            ('÷', 3, self._btn_style_orange),
        ]:
            btn = self._make_button(label, style)
            grid.addWidget(btn, row, col)

        row = 2
        for label, col, style in [
            ('7', 0, self._btn_style_dark),
            ('8', 1, self._btn_style_dark),
            ('9', 2, self._btn_style_dark),
            ('×', 3, self._btn_style_orange),
        ]:
            btn = self._make_button(label, style)
            grid.addWidget(btn, row, col)

        row = 3
        for label, col, style in [
            ('4', 0, self._btn_style_dark),
            ('5', 1, self._btn_style_dark),
            ('6', 2, self._btn_style_dark),
            ('-', 3, self._btn_style_orange),
        ]:
            btn = self._make_button(label, style)
            grid.addWidget(btn, row, col)

        row = 4
        for label, col, style in [
            ('1', 0, self._btn_style_dark),
            ('2', 1, self._btn_style_dark),
            ('3', 2, self._btn_style_dark),
            ('+', 3, self._btn_style_orange),
        ]:
            btn = self._make_button(label, style)
            grid.addWidget(btn, row, col)

        row = 5
        btn0 = self._make_button('0', self._btn_style_dark)
        grid.addWidget(btn0, row, 0, 1, 2)
        btn_dot = self._make_button('.', self._btn_style_dark)
        grid.addWidget(btn_dot, row, 2)
        btn_eq = self._make_button('=', self._btn_style_orange)
        grid.addWidget(btn_eq, row, 3)

        self.setLayout(grid)
        self.setStyleSheet('background-color: #000000;')

    def _make_button(self, text: str, stylesheet: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(stylesheet)
        btn.clicked.connect(lambda checked=False, t=text: self._on_button(t))
        return btn

    def _refresh_display(self):
        if self._entry == 'Error':
            self._display.setText('Error')
            return
        self._display.setText(format_display(self._entry))

    def _on_button(self, text: str):
        if self._entry == 'Error' and text != 'AC':
            return
        if text == 'AC':
            self._entry = '0'
            self._stored = None
            self._pending_op = None
            self._fresh = True
            self._refresh_display()
            return
        if text in '0123456789':
            self._digit(text)
            return
        if text == '.':
            self._dot()
            return
        if text == '+/-':
            self._toggle_sign()
            return
        if text == '%':
            self._percent()
            return
        if text in ('+', '-', '×', '÷'):
            self._operator(text)
            return
        if text == '=':
            self._equals()

    def _digit(self, d: str):
        if self._fresh:
            self._entry = d if d != '0' else '0'
            self._fresh = False
            self._refresh_display()
            return
        if self._entry == '0' and d != '0':
            self._entry = d
        elif self._entry == '0' and d == '0':
            pass
        elif self._entry == '-0':
            self._entry = f'-{d}' if d != '0' else '-0'
        else:
            self._entry += d
        self._refresh_display()

    def _dot(self):
        if self._fresh:
            self._entry = '0.'
            self._fresh = False
            self._refresh_display()
            return
        if '.' in self._entry:
            return
        self._entry += '.'
        self._refresh_display()

    def _toggle_sign(self):
        if self._entry in ('0', '0.'):
            self._entry = '-0' if self._entry == '0' else '-0.'
            self._fresh = False
            self._refresh_display()
            return
        if self._entry.startswith('-'):
            self._entry = self._entry[1:]
        else:
            self._entry = '-' + self._entry
        self._refresh_display()

    def _percent(self):
        try:
            v = float(self._entry)
        except ValueError:
            self._entry = 'Error'
            self._refresh_display()
            return
        self._entry = self._normalize_number(v / 100.0)
        self._fresh = True
        self._refresh_display()

    def _operator(self, op: str):
        try:
            cur = float(self._entry)
        except ValueError:
            self._entry = 'Error'
            self._refresh_display()
            return
        if self._stored is not None and self._pending_op is not None and not self._fresh:
            res = self._apply(self._stored, cur, self._pending_op)
            if res is None:
                self._entry = 'Error'
                self._stored = None
                self._pending_op = None
            else:
                self._stored = res
                self._entry = self._normalize_number(res)
        else:
            self._stored = cur
        self._pending_op = op
        self._fresh = True
        self._refresh_display()

    def _equals(self):
        if self._pending_op is None or self._stored is None:
            self._fresh = True
            return
        try:
            cur = float(self._entry)
        except ValueError:
            self._entry = 'Error'
            self._refresh_display()
            return
        res = self._apply(self._stored, cur, self._pending_op)
        if res is None:
            self._entry = 'Error'
        else:
            self._entry = self._normalize_number(res)
        self._stored = None
        self._pending_op = None
        self._fresh = True
        self._refresh_display()

    def _apply(self, left: float, right: float, op: str):
        if op == '+':
            return left + right
        if op == '-':
            return left - right
        if op == '×':
            return left * right
        if op == '÷':
            if right == 0:
                return None
            return left / right
        return None

    def _normalize_number(self, value: float) -> str:
        if not (value == value):
            return 'Error'
        if value in (float('inf'), float('-inf')):
            return 'Error'
        s = f'{value:.12g}'
        if 'e' in s.lower():
            return s
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s if s else '0'


def main():
    app = QApplication(sys.argv)
    window = Calculator()
    window.resize(360, 520)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
