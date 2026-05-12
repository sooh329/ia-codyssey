import itertools
import multiprocessing
import os
import string
import sys
import traceback
import zipfile
import zlib
from datetime import datetime


DEFAULT_ZIP_FILENAME = 'emergency_storage_key.zip'
DEFAULT_PASSWORD_FILENAME = 'password.txt'
PASSWORD_LEN = 6
FORCED_PREFIX = 'mars'

_STOP_EVENT = None


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _init_worker(stop_event):
    global _STOP_EVENT
    _STOP_EVENT = stop_event


def _check_password(zf, entry_name, password_bytes):
    """Return True if password decrypts; read only 1 byte (not whole file)."""
    try:
        with zf.open(entry_name, 'r', pwd=password_bytes) as file:
            file.read(1)
        return True
    except (
        RuntimeError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        zlib.error,
        OSError,
    ):
        return False


def _crack_worker(args):
    """
    Try all passwords with a fixed first character.
    Returns the password string if found, else None.
    """
    zip_path, prefix, charset, log_every, debug = args

    if _STOP_EVENT is not None and _STOP_EVENT.is_set():
        return None

    zf = None
    tries = 0
    try:
        zf = zipfile.ZipFile(zip_path, 'r')
        names = zf.namelist()
        if not names:
            return None
        entry_name = names[0]

        for combo in itertools.product(charset, repeat=PASSWORD_LEN - len(prefix)):
            if _STOP_EVENT is not None and _STOP_EVENT.is_set():
                return None

            password = prefix + ''.join(combo)
            pwd_bytes = password.encode('utf-8')
            tries += 1

            if log_every and (tries % log_every == 0):
                print(f'[{os.getpid()}] tried: {password}', flush=True)

            if _check_password(zf, entry_name, pwd_bytes):
                if _STOP_EVENT is not None:
                    _STOP_EVENT.set()
                return password

    except Exception:
        if debug:
            print(f'[{os.getpid()}] worker error (prefix={prefix!r}):', file=sys.stderr, flush=True)
            traceback.print_exc()
        return None
    finally:
        if zf is not None:
            try:
                zf.close()
            except Exception:
                pass

    return None


def unlock_zip(
    zip_path=None,
    output_path=None,
    prefix='',
    log_every=0,
    debug=False,
):
    """
    Brute-force zip password (6 chars: lowercase + digits). Saves to password.txt on success.
    Paths default to files next to this script so cwd does not matter.

    Uses only a tiny read per guess (not ZipFile.read which decompresses the whole entry).
    """
    if prefix is None:
        prefix = ''
    prefix = str(prefix)
    if len(prefix) > PASSWORD_LEN:
        print(f'ERROR: prefix too long (len={len(prefix)}), PASSWORD_LEN={PASSWORD_LEN}')
        return None

    here = _script_dir()
    if zip_path is None:
        zip_path = os.path.join(here, DEFAULT_ZIP_FILENAME)
    else:
        zip_path = os.path.abspath(zip_path)
    if output_path is None:
        output_path = os.path.join(here, DEFAULT_PASSWORD_FILENAME)
    else:
        output_path = os.path.abspath(output_path)

    if not os.path.isfile(zip_path):
        print(f'ERROR: file not found: {zip_path}')
        print(f'Hint: place {DEFAULT_ZIP_FILENAME} in {_script_dir()}')
        return None

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf_check:
            if not zf_check.namelist():
                print(f'ERROR: zip has no entries: {zip_path}')
                return None
    except zipfile.BadZipFile:
        print(f'ERROR: not a valid zip file: {zip_path}')
        return None
    except OSError as exc:
        print(f'ERROR: cannot open zip: {exc}')
        return None

    charset = string.ascii_lowercase + string.digits
    cpu_count = multiprocessing.cpu_count() or 1

    try:
        log_every = int(log_every or 0)
    except (TypeError, ValueError):
        log_every = 0

    start_time = datetime.now()
    print(f'start time: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'cpu cores: {cpu_count}')
    if prefix:
        remaining = PASSWORD_LEN - len(prefix)
        print(f'prefix: {prefix!r} (remaining length: {remaining})')
        print(f'search space: {len(charset)}^{remaining} = {len(charset) ** remaining:,}')
    else:
        print(f'search space: {len(charset)}^{PASSWORD_LEN} = {len(charset) ** PASSWORD_LEN:,}')
        print(f'per worker (1 leading char fixed): {len(charset) ** (PASSWORD_LEN - 1):,}')
    print('note: using open().read(1) per guess (much faster than ZipFile.read whole file)')

    stop_event = multiprocessing.Event()

    if prefix:
        remaining = PASSWORD_LEN - len(prefix)
        if remaining <= 0:
            tasks = [(zip_path, prefix, charset, log_every, debug)]
        elif remaining == 1:
            tasks = [(zip_path, prefix + char, charset, log_every, debug) for char in charset]
        else:
            # Parallelize by fixing the next character after the prefix.
            tasks = [(zip_path, prefix + char, charset, log_every, debug) for char in charset]
            print(f'per worker (prefix + 1 char fixed): {len(charset) ** (remaining - 1):,}')
    else:
        tasks = [(zip_path, char, charset, log_every, debug) for char in charset]

    found_password = None
    pool = multiprocessing.Pool(
        processes=cpu_count,
        initializer=_init_worker,
        initargs=(stop_event,),
    )
    try:
        for result in pool.imap_unordered(_crack_worker, tasks, chunksize=1):
            if result:
                found_password = result
                stop_event.set()
                break
    finally:
        pool.terminate()
        pool.join()

    elapsed = datetime.now() - start_time

    if found_password:
        print(f'\npassword found: {found_password}')
        print(f'elapsed: {elapsed}')
        try:
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(found_password)
            print(f'saved to: {output_path}')
        except OSError as exc:
            print(f'ERROR: failed to save file: {exc}')
            return None
        return found_password

    print('\npassword not found')
    print(f'elapsed: {elapsed}')
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Brute-force zip password (lowercase + digits).')
    parser.add_argument('--zip', dest='zip_path', default=None, help='Path to zip file.')
    parser.add_argument('--out', dest='output_path', default=None, help='Path to save found password.')
    parser.add_argument(
        '--log-every',
        dest='log_every',
        default=0,
        help='Print progress every N attempts per worker. Use 1 to log every try (very noisy).',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print worker exceptions to stderr (helps when nothing seems to happen).',
    )
    args = parser.parse_args()
    unlock_zip(
        zip_path=args.zip_path,
        output_path=args.output_path,
        prefix=FORCED_PREFIX,
        log_every=args.log_every,
        debug=args.debug,
    )


if __name__ == '__main__':
    main()
