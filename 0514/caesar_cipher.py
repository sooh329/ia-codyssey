import os


DEFAULT_PASSWORD_FILENAME = 'password.txt'
DEFAULT_RESULT_FILENAME = 'result.txt'
ALPHABET_SIZE = 26

DEFAULT_DICTIONARY = (
    'mars',
    'earth',
    'open',
    'door',
    'storage',
    'emergency',
    'key',
    'password',
    'secret',
    'access',
    'unlock',
    'oxygen',
    'water',
    'food',
    'base',
    'station',
    'hello',
    'world',
    'hatch',
    'rover',
    'venus',
    'mission',
    'computer',
)


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _shift_text(text, shift):
    """Shift letters by ``shift`` positions (left, i.e. decode direction)."""
    shift = shift % ALPHABET_SIZE
    result_chars = []
    for ch in text:
        if 'a' <= ch <= 'z':
            offset = (ord(ch) - ord('a') - shift) % ALPHABET_SIZE
            result_chars.append(chr(ord('a') + offset))
        elif 'A' <= ch <= 'Z':
            offset = (ord(ch) - ord('A') - shift) % ALPHABET_SIZE
            result_chars.append(chr(ord('A') + offset))
        else:
            result_chars.append(ch)
    return ''.join(result_chars)


def caesar_cipher_decode(target_text, dictionary=DEFAULT_DICTIONARY):
    """
    Try every Caesar shift (0..25) on ``target_text`` and print each result.

    If ``dictionary`` is given (non-empty), the loop stops early when a
    dictionary word is found inside the decoded text (bonus task), and the
    matching shift number is returned. Otherwise returns None.
    """
    if not isinstance(target_text, str):
        raise TypeError('target_text must be a string')

    normalized_dict = set()
    if dictionary:
        for word in dictionary:
            if isinstance(word, str) and word:
                normalized_dict.add(word.lower())

    print(f'Target text: {target_text}')
    print('-' * 60)

    matched_shift = None
    for shift in range(ALPHABET_SIZE):
        decoded = _shift_text(target_text, shift)
        print(f'shift {shift:2d}: {decoded}')

        if normalized_dict:
            lowered = decoded.lower()
            for word in normalized_dict:
                if word in lowered:
                    print(f'  -> dictionary match: "{word}" (auto-stop)')
                    matched_shift = shift
                    break
            if matched_shift is not None:
                break

    return matched_shift


def _read_target_text(path):
    with open(path, 'r', encoding='utf-8') as file:
        text = file.read()
    return text.strip()


def _save_result(path, text):
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        file.write(text)


def _ask_shift_number():
    while True:
        try:
            user_input = input(
                'Enter the shift number that looks correct '
                '(0-25, empty to cancel): '
            ).strip()
        except EOFError:
            return None

        if user_input == '':
            return None

        try:
            shift = int(user_input)
        except ValueError:
            print('Please enter a valid integer.')
            continue

        if 0 <= shift < ALPHABET_SIZE:
            return shift
        print(f'Shift must be between 0 and {ALPHABET_SIZE - 1}.')


def main():
    here = _script_dir()
    password_path = os.path.join(here, DEFAULT_PASSWORD_FILENAME)
    result_path = os.path.join(here, DEFAULT_RESULT_FILENAME)

    try:
        target_text = _read_target_text(password_path)
    except FileNotFoundError:
        print(f'ERROR: file not found: {password_path}')
        print(f'Hint: place {DEFAULT_PASSWORD_FILENAME} in {here}')
        return
    except OSError as exc:
        print(f'ERROR: cannot read file: {exc}')
        return

    if not target_text:
        print(f'ERROR: file is empty: {password_path}')
        return

    matched_shift = caesar_cipher_decode(target_text)

    if matched_shift is not None:
        decoded = _shift_text(target_text, matched_shift)
        print(f'\nAuto-detected shift: {matched_shift}')
        print(f'Decoded text: {decoded}')
        chosen_shift = matched_shift
    else:
        chosen_shift = _ask_shift_number()
        if chosen_shift is None:
            print('No shift selected. Result file was not written.')
            return
        decoded = _shift_text(target_text, chosen_shift)
        print(f'Selected shift {chosen_shift}: {decoded}')

    try:
        _save_result(result_path, decoded)
        print(f'Saved decoded result to: {result_path}')
    except OSError as exc:
        print(f'ERROR: failed to save result: {exc}')


if __name__ == '__main__':
    main()
