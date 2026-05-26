import os
import struct
import wave
from datetime import datetime


RECORDS_DIRNAME = 'records'
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1
FILENAME_TIME_FORMAT = '%Y%m%d-%H%M%S'


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def get_records_dir():
    return os.path.join(_script_dir(), RECORDS_DIRNAME)


def ensure_records_dir():
    records_dir = get_records_dir()
    try:
        os.makedirs(records_dir, exist_ok=True)
    except OSError as exc:
        raise OSError(f'cannot create records folder: {records_dir} ({exc})') from exc
    return records_dir


def build_record_filename(when=None):
    """
    Build a filename like YYYYMMDD-HHMMSS.wav from a datetime (or now).
    """
    if when is None:
        when = datetime.now()
    stamp = when.strftime(FILENAME_TIME_FORMAT)
    return f'{stamp}.wav'


def _import_sounddevice():
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise ImportError(
            'sounddevice is required for microphone recording. '
            'Install it with: pip install sounddevice'
        ) from exc
    return sd


def list_input_devices():
    """
    Print available audio input devices (microphones).
    Returns the number of input-capable devices found.
    """
    sd = _import_sounddevice()
    try:
        devices = sd.query_devices()
    except Exception as exc:
        print(f'ERROR: cannot query audio devices: {exc}')
        return 0

    count = 0
    print('Available audio input devices:')
    print('-' * 60)
    for index, device in enumerate(devices):
        max_input = device.get('max_input_channels', 0)
        if max_input and max_input > 0:
            count += 1
            name = device.get('name', 'unknown')
            print(f'  [{index}] {name} (inputs: {max_input})')
    print('-' * 60)
    if count == 0:
        print('No microphone input devices were found.')
    else:
        print(f'Total input devices: {count}')
    return count


def record_from_microphone(duration_seconds, sample_rate=DEFAULT_SAMPLE_RATE, channels=DEFAULT_CHANNELS):
    """
    Record audio from the default system microphone.

    Returns (frames_bytes, sample_rate, channels).
    """
    if duration_seconds <= 0:
        raise ValueError('duration_seconds must be positive')

    sd = _import_sounddevice()
    frame_count = int(duration_seconds * sample_rate)

    try:
        recording = sd.rec(
            frame_count,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
        )
        sd.wait()
    except Exception as exc:
        raise RuntimeError(f'microphone recording failed: {exc}') from exc

    if hasattr(recording, 'tobytes'):
        frames = recording.tobytes()
    else:
        flat = recording.flatten() if hasattr(recording, 'flatten') else recording
        frames = b''.join(struct.pack('<h', int(sample)) for sample in flat)

    return frames, sample_rate, channels


def save_wav_file(file_path, frames, sample_rate, channels):
    try:
        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(frames)
    except OSError as exc:
        raise OSError(f'cannot write wav file: {file_path} ({exc})') from exc


def save_recording(frames, sample_rate, channels, when=None):
    records_dir = ensure_records_dir()
    filename = build_record_filename(when=when)
    file_path = os.path.join(records_dir, filename)
    save_wav_file(file_path, frames, sample_rate, channels)
    return file_path


def _parse_record_timestamp(filename):
    base, ext = os.path.splitext(filename)
    if ext.lower() != '.wav':
        return None
    try:
        return datetime.strptime(base, FILENAME_TIME_FORMAT)
    except ValueError:
        return None


def list_recordings_in_range(start_ymd, end_ymd):
    """
    Bonus: list recording files whose names fall between start_ymd and end_ymd.

    Dates are strings like '20260501' and '20260531' (YYYYMMDD).
    """
    try:
        start_date = datetime.strptime(start_ymd, '%Y%m%d').date()
        end_date = datetime.strptime(end_ymd, '%Y%m%d').date()
    except ValueError:
        print('ERROR: dates must be YYYYMMDD (example: 20260501)')
        return []

    if start_date > end_date:
        print('ERROR: start date must not be after end date')
        return []

    records_dir = get_records_dir()
    if not os.path.isdir(records_dir):
        print(f'No records folder yet: {records_dir}')
        return []

    matched = []
    try:
        names = os.listdir(records_dir)
    except OSError as exc:
        print(f'ERROR: cannot read records folder: {exc}')
        return []

    for name in sorted(names):
        recorded_at = _parse_record_timestamp(name)
        if recorded_at is None:
            continue
        day = recorded_at.date()
        if start_date <= day <= end_date:
            matched.append(os.path.join(records_dir, name))

    print(f'Recordings from {start_ymd} to {end_ymd}:')
    if not matched:
        print('  (none)')
    else:
        for path in matched:
            print(f'  {path}')
    return matched


def run_recording_session():
    try:
        duration_text = input('Recording length in seconds: ').strip()
        duration = float(duration_text)
    except EOFError:
        print('Cancelled.')
        return
    except ValueError:
        print('ERROR: enter a number for duration.')
        return

    print('Listing microphones...')
    list_input_devices()
    print(f'Recording for {duration} second(s)...')
    try:
        frames, sample_rate, channels = record_from_microphone(duration)
        saved_path = save_recording(frames, sample_rate, channels)
    except (ImportError, ValueError, RuntimeError, OSError) as exc:
        print(f'ERROR: {exc}')
        return

    print(f'Saved recording: {saved_path}')


def run_date_range_listing():
    try:
        start_ymd = input('Start date (YYYYMMDD): ').strip()
        end_ymd = input('End date (YYYYMMDD): ').strip()
    except EOFError:
        print('Cancelled.')
        return
    list_recordings_in_range(start_ymd, end_ymd)


def main():
    ensure_records_dir()
    print('Javis voice recorder')
    print(f'Records folder: {get_records_dir()}')

    while True:
        print()
        print('1) List microphones')
        print('2) Record and save')
        print('3) List recordings by date range (bonus)')
        print('4) Exit')
        try:
            choice = input('Select: ').strip()
        except EOFError:
            print()
            break

        if choice == '1':
            list_input_devices()
        elif choice == '2':
            run_recording_session()
        elif choice == '3':
            run_date_range_listing()
        elif choice == '4':
            print('Goodbye.')
            break
        else:
            print('Invalid choice.')


if __name__ == '__main__':
    main()
