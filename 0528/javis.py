import csv
import os
import struct
import wave
from datetime import datetime


RECORDS_DIRNAME = 'records'
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1
FILENAME_TIME_FORMAT = '%Y%m%d-%H%M%S'

DEFAULT_STT_LANGUAGE = 'ko-KR'
DEFAULT_CHUNK_SECONDS = 8.0


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


def _import_speech_recognition():
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise ImportError(
            'speechrecognition is required for STT. '
            'Install it with: pip install SpeechRecognition'
        ) from exc
    return sr


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
    List recording files whose names fall between start_ymd and end_ymd.

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


def find_records_dirs(root_dir):
    """
    Find all folders named 'records' under root_dir.
    """
    found = []
    for dir_path, dir_names, _file_names in os.walk(root_dir):
        base = os.path.basename(dir_path)
        if base == RECORDS_DIRNAME:
            found.append(dir_path)
            dir_names[:] = []
    return found


def list_all_recordings(search_root=None):
    """
    Load recording file list from problem 7.

    If current script's records folder is empty, also searches other 'records' folders
    under the workspace.
    """
    if search_root is None:
        search_root = os.path.dirname(_script_dir())

    primary_dir = get_records_dir()
    candidates = []
    if os.path.isdir(primary_dir):
        candidates.append(primary_dir)

    for records_dir in find_records_dirs(search_root):
        if records_dir not in candidates:
            candidates.append(records_dir)

    recordings = []
    for records_dir in candidates:
        try:
            names = os.listdir(records_dir)
        except OSError:
            continue
        for name in names:
            if name.lower().endswith('.wav'):
                recordings.append(os.path.join(records_dir, name))

    recordings.sort()
    print('Found recordings:')
    if not recordings:
        print('  (none)')
        return []
    for path in recordings:
        print(f'  {path}')
    return recordings


def _format_timestamp(seconds):
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def _iter_wav_chunks(file_path, chunk_seconds):
    """
    Yield (start_seconds, bytes, sample_rate, sample_width) for each chunk.
    """
    if chunk_seconds <= 0:
        raise ValueError('chunk_seconds must be positive')

    with wave.open(file_path, 'rb') as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        total_frames = wav_file.getnframes()

        if channels != 1:
            raise ValueError('only mono wav files are supported for STT')
        if sample_width != 2:
            raise ValueError('only 16-bit wav files are supported for STT')

        frames_per_chunk = int(round(chunk_seconds * sample_rate))
        if frames_per_chunk <= 0:
            frames_per_chunk = 1

        current_frame = 0
        while current_frame < total_frames:
            start_seconds = current_frame / float(sample_rate)
            remaining = total_frames - current_frame
            to_read = frames_per_chunk if remaining > frames_per_chunk else remaining
            frames = wav_file.readframes(to_read)
            if not frames:
                break
            yield start_seconds, frames, sample_rate, sample_width
            current_frame += to_read


def transcribe_wav_to_csv(file_path, csv_path=None, language=DEFAULT_STT_LANGUAGE, chunk_seconds=DEFAULT_CHUNK_SECONDS):
    """
    Transcribe a wav file into a CSV with rows:
      time_in_audio, recognized_text
    """
    sr = _import_speech_recognition()

    if csv_path is None:
        base, _ext = os.path.splitext(file_path)
        csv_path = f'{base}.CSV'

    recognizer = sr.Recognizer()
    rows = []
    for start_seconds, frames, sample_rate, sample_width in _iter_wav_chunks(file_path, chunk_seconds):
        audio = sr.AudioData(frames, sample_rate, sample_width)
        try:
            text = recognizer.recognize_google(audio, language=language)
        except sr.UnknownValueError:
            text = ''
        except sr.RequestError as exc:
            raise RuntimeError(f'STT request failed: {exc}') from exc

        rows.append((_format_timestamp(start_seconds), text))

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for time_text, text in rows:
                writer.writerow([time_text, text])
    except OSError as exc:
        raise OSError(f'cannot write csv file: {csv_path} ({exc})') from exc

    return csv_path, rows


def transcribe_recordings_flow():
    recordings = list_all_recordings()
    if not recordings:
        return

    try:
        lang = input(f'Language (default: {DEFAULT_STT_LANGUAGE}): ').strip()
        chunk_text = input(f'Chunk seconds (default: {DEFAULT_CHUNK_SECONDS}): ').strip()
    except EOFError:
        print('Cancelled.')
        return

    language = lang if lang else DEFAULT_STT_LANGUAGE
    if chunk_text:
        try:
            chunk_seconds = float(chunk_text)
        except ValueError:
            print('ERROR: chunk seconds must be a number.')
            return
    else:
        chunk_seconds = DEFAULT_CHUNK_SECONDS

    for path in recordings:
        print()
        print(f'Transcribing: {path}')
        try:
            csv_path, rows = transcribe_wav_to_csv(path, language=language, chunk_seconds=chunk_seconds)
        except (ImportError, ValueError, RuntimeError, OSError) as exc:
            print(f'ERROR: {exc}')
            continue

        non_empty = sum(1 for _t, text in rows if text)
        print(f'Saved CSV: {csv_path} (rows: {len(rows)}, non-empty: {non_empty})')


def search_csv_files_for_keyword(keyword, search_root=None):
    if not keyword:
        print('ERROR: keyword is empty.')
        return

    if search_root is None:
        search_root = os.path.dirname(_script_dir())

    matches = 0
    for dir_path, _dir_names, file_names in os.walk(search_root):
        for name in file_names:
            if not name.lower().endswith('.csv'):
                continue
            csv_path = os.path.join(dir_path, name)
            try:
                with open(csv_path, 'r', newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    for row in reader:
                        if len(row) < 2:
                            continue
                        time_text = row[0].strip()
                        text = row[1].strip()
                        if keyword in text:
                            if matches == 0:
                                print('Matches:')
                            matches += 1
                            print(f'  {csv_path} | {time_text} | {text}')
            except OSError:
                continue

    if matches == 0:
        print('No matches were found.')
    else:
        print(f'Total matches: {matches}')


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


def run_keyword_search():
    try:
        keyword = input('Keyword to search in CSV: ').strip()
    except EOFError:
        print('Cancelled.')
        return
    search_csv_files_for_keyword(keyword)


def main():
    ensure_records_dir()
    print('Javis voice recorder + STT')
    print(f'Records folder: {get_records_dir()}')

    while True:
        print()
        print('1) List microphones')
        print('2) Record and save')
        print('3) List recordings by date range')
        print('4) List all recordings (problem 7)')
        print('5) STT recordings -> CSV')
        print('6) Search keyword in saved CSV (bonus)')
        print('7) Exit')
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
            list_all_recordings()
        elif choice == '5':
            transcribe_recordings_flow()
        elif choice == '6':
            run_keyword_search()
        elif choice == '7':
            print('Goodbye.')
            break
        else:
            print('Invalid choice.')


if __name__ == '__main__':
    main()

