import itertools
import multiprocessing
import os
import string
import zipfile
import zlib
from datetime import datetime


DEFAULT_ZIP_FILENAME = 'emergency_storage_key.zip'
DEFAULT_PASSWORD_FILENAME = 'password.txt'
PASSWORD_LEN = 6

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
    zip_path, prefix, charset = args

    if _STOP_EVENT is not None and _STOP_EVENT.is_set():
        return None

    zf = None
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

            if _check_password(zf, entry_name, pwd_bytes):
                if _STOP_EVENT is not None:
                    _STOP_EVENT.set()
                return password

    except Exception:
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
):
    """
    Brute-force zip password (6 chars: lowercase + digits). Saves to password.txt on success.
    Paths default to files next to this script so cwd does not matter.

    Uses only a tiny read per guess (not ZipFile.read which decompresses the whole entry).
    """
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

    start_time = datetime.now()
    print(f'start time: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'cpu cores: {cpu_count}')
    print(f'search space: {len(charset)}^{PASSWORD_LEN} = {len(charset) ** PASSWORD_LEN:,}')
    print(f'per worker (1 leading char fixed): {len(charset) ** (PASSWORD_LEN - 1):,}')
    print('note: using open().read(1) per guess (much faster than ZipFile.read whole file)')

    stop_event = multiprocessing.Event()

    tasks = [(zip_path, char, charset) for char in charset]

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
    unlock_zip()


if __name__ == '__main__':
    main()
