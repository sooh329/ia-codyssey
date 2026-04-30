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


MAX_ABS_VALUE = 1e100


def add_thousands_commas(text):
    if not text or text == '-':
        return text
    neg = text.startswith('-')
    digits = text[1:] if neg else text
    digits = digits.lstrip('0') or '0'
    out = []
    for i, ch in enumerate(reversed(digits)):
        if i and i % 3 == 0:
            out.append(',')
        out.append(ch)
    grouped = ''.join(reversed(out))
    return f'-{grouped}' if neg else grouped


def format_display_value(raw):
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
        return f'{add_thousands_commas(base)}.'
    if '.' in raw:
        int_part, frac_part = raw.split('.', 1)
        if int_part in ('', '-'):
            int_view = '0' if int_part == '' else '-0'
        else:
            int_view = add_thousands_commas(int_part)
        return f'{int_view}.{frac_part}'
    return add_thousands_commas(raw)


class Calculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.current = '0'
        self.stored = None
        self.operator = None
        self.fresh = True
        return self.current

    def input_digit(self, digit):
        if self.current == 'Error':
            return self.current
        if self.fresh:
            self.current = digit if digit != '0' else '0'
            self.fresh = False
            return self.current
        if self.current == '0':
            self.current = digit if digit != '0' else '0'
        elif self.current == '-0':
            self.current = f'-{digit}' if digit != '0' else '-0'
        else:
            self.current += digit
        return self.current

    def input_decimal(self):
        if self.current == 'Error':
            return self.current
        if self.fresh:
            self.current = '0.'
            self.fresh = False
            return self.current
        if '.' not in self.current:
            self.current += '.'
        return self.current

    def negative_positive(self):
        if self.current == 'Error':
            return self.current
        if self.current in ('0', '0.'):
            self.current = '-0' if self.current == '0' else '-0.'
            self.fresh = False
            return self.current
        if self.current.startswith('-'):
            self.current = self.current[1:]
        else:
            self.current = '-' + self.current
        return self.current

    def percent(self):
        value = self._to_number(self.current)
        if value is None:
            self.current = 'Error'
            return self.current
        result = value / 100.0
        return self._set_result(result)

    def add(self, left, right):
        return left + right

    def subtract(self, left, right):
        return left - right

    def multiply(self, left, right):
        return left * right

    def divide(self, left, right):
        if right == 0:
            return None
        return left / right

    def set_operator(self, op):
        value = self._to_number(self.current)
        if value is None:
            self.current = 'Error'
            return self.current
        if self.operator is not None and self.stored is not None and not self.fresh:
            partial = self._calculate(self.stored, value, self.operator)
            if partial is None:
                self.current = 'Error'
                self.stored = None
                self.operator = None
                return self.current
            self.stored = partial
            normalized = self._normalize_result(partial)
            if normalized is None:
                self.current = 'Error'
                self.stored = None
                self.operator = None
                return self.current
            self.current = normalized
        else:
            self.stored = value
        self.operator = op
        self.fresh = True
        return self.current

    def equal(self):
        if self.operator is None or self.stored is None:
            self.fresh = True
            return self.current
        right = self._to_number(self.current)
        if right is None:
            self.current = 'Error'
            self.operator = None
            self.stored = None
            return self.current
        result = self._calculate(self.stored, right, self.operator)
        self.operator = None
        self.stored = None
        if result is None:
            self.current = 'Error'
            self.fresh = True
            return self.current
        return self._set_result(result)

    def _set_result(self, value):
        normalized = self._normalize_result(value)
        if normalized is None:
            self.current = 'Error'
        else:
            self.current = normalized
        self.fresh = True
        return self.current

    def _calculate(self, left, right, op):
        if op == '+':
            return self.add(left, right)
        if op == '-':
            return self.subtract(left, right)
        if op == '×':
            return self.multiply(left, right)
        if op == '÷':
            return self.divide(left, right)
        return None

    def _to_number(self, text):
        try:
            return float(text)
        except Exception:
            return None

    def _normalize_result(self, value):
        if not (value == value):
            return None
        if value in (float('inf'), float('-inf')):
            return None
        if abs(value) > MAX_ABS_VALUE:
            return None

        rounded = round(value, 6)
        text = f'{rounded:.6f}'.rstrip('0').rstrip('.')
        if text == '-0':
            text = '0'
        return text or '0'


class CalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Calculator')
        self.calculator = Calculator()

        self.display = QLabel('0')
        self.display.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.display.setMinimumHeight(96)
        self.display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._apply_display_font(1)
        self.display.setStyleSheet(
            'QLabel { background-color: #000000; color: #ffffff; padding: 12px 16px; }'
        )

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.addWidget(self.display, 0, 0, 1, 4)

        style_gray = (
            'QPushButton { background-color: #a6a6a6; color: #000000; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #d0d0d0; }'
        )
        style_dark = (
            'QPushButton { background-color: #333333; color: #ffffff; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #5a5a5a; }'
        )
        style_orange = (
            'QPushButton { background-color: #ff9500; color: #ffffff; border: none; '
            'border-radius: 36px; font-size: 28px; min-height: 72px; }'
            'QPushButton:pressed { background-color: #e68600; }'
        )

        rows = [
            [('AC', style_gray), ('+/-', style_gray), ('%', style_gray), ('÷', style_orange)],
            [('7', style_dark), ('8', style_dark), ('9', style_dark), ('×', style_orange)],
            [('4', style_dark), ('5', style_dark), ('6', style_dark), ('-', style_orange)],
            [('1', style_dark), ('2', style_dark), ('3', style_dark), ('+', style_orange)],
        ]

        start_row = 1
        for r_idx, row in enumerate(rows):
            for c_idx, (label, style) in enumerate(row):
                grid.addWidget(self._make_button(label, style), start_row + r_idx, c_idx)

        grid.addWidget(self._make_button('0', style_dark), 5, 0, 1, 2)
        grid.addWidget(self._make_button('.', style_dark), 5, 2)
        grid.addWidget(self._make_button('=', style_orange), 5, 3)

        self.setLayout(grid)
        self.setStyleSheet('background-color: #000000;')

    def _make_button(self, text, style):
        button = QPushButton(text)
        button.setStyleSheet(style)
        button.clicked.connect(lambda checked=False, t=text: self._on_button_clicked(t))
        return button

    def _apply_display_font(self, length):
        size = 36
        if length > 9:
            size = 32
        if length > 12:
            size = 28
        if length > 15:
            size = 24
        if length > 18:
            size = 20
        font = QFont('Segoe UI', size)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.display.setFont(font)

    def _sync_display(self):
        text = self.calculator.current
        shown = text if text == 'Error' else format_display_value(text)
        self._apply_display_font(len(shown))
        self.display.setText(shown)

    def _on_button_clicked(self, text):
        if text in '0123456789':
            self.calculator.input_digit(text)
        elif text == '.':
            self.calculator.input_decimal()
        elif text == 'AC':
            self.calculator.reset()
        elif text == '+/-':
            self.calculator.negative_positive()
        elif text == '%':
            self.calculator.percent()
        elif text in ('+', '-', '×', '÷'):
            self.calculator.set_operator(text)
        elif text == '=':
            self.calculator.equal()
        self._sync_display()


def main():
    app = QApplication(sys.argv)
    window = CalculatorWindow()
    window.resize(360, 520)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
