import csv
import os
import struct
import zlib
from datetime import datetime


CSV_FILENAME = 'mars_weathers_data.csv'
PNG_FILENAME = 'mars_weather_summary.png'
TABLE_NAME = 'mars_weather'

DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = 'kkdk1007'
DB_NAME = 'codyssey'

DATE_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
)

CHART_WIDTH = 900
CHART_HEIGHT = 500
CHART_MARGIN = 60


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _import_mysql_connector():
    try:
        import mysql.connector
    except ImportError as exc:
        raise ImportError(
            'mysql-connector-python is required for MySQL. '
            'Install it with: pip install mysql-connector-python'
        ) from exc
    return mysql.connector


class MySQLHelper:
    """
    Helper for MySQL connection and query execution.
    """

    def __init__(self, host, user, password, database, port=3306):
        self._host = host
        self._user = user
        self._password = password
        self._database = database
        self._port = port
        self._connection = None
        self._cursor = None

    def connect(self):
        connector = _import_mysql_connector()
        self._connection = connector.connect(
            host=self._host,
            user=self._user,
            password=self._password,
            database=self._database,
            port=self._port,
        )
        self._cursor = self._connection.cursor()
        return self

    def close(self):
        if self._cursor is not None:
            self._cursor.close()
            self._cursor = None
        if self._connection is not None and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    def execute(self, query, params=None):
        if self._cursor is None:
            raise RuntimeError('database is not connected')
        self._cursor.execute(query, params or ())
        self._connection.commit()

    def fetch_all(self, query, params=None):
        if self._cursor is None:
            raise RuntimeError('database is not connected')
        self._cursor.execute(query, params or ())
        return self._cursor.fetchall()


def parse_mars_datetime(value):
    text = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    raise ValueError(f'unsupported date format: {value}')


def _normalize_row(row):
    # csv columns: weather_id, mars_date, temp, stom(storm)
    if len(row) < 4:
        raise ValueError(f'invalid csv row: {row}')

    mars_date = parse_mars_datetime(row[1])
    temp = int(round(float(row[2])))
    storm = int(row[3])
    return mars_date, temp, storm


def read_mars_weather_csv(file_path):
    rows = []
    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as csv_file:
            reader = csv.reader(csv_file)
            for index, row in enumerate(reader):
                if not row or all(not cell.strip() for cell in row):
                    continue

                if index == 0 and not row[0].strip().isdigit():
                    continue

                rows.append(_normalize_row(row))
    except OSError as exc:
        raise OSError(f'cannot read csv file: {file_path} ({exc})') from exc

    return rows


def print_csv_contents(file_path):
    print(f'=== {os.path.basename(file_path)} contents ===')
    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as csv_file:
            for line in csv_file:
                print(line.rstrip('\n'))
    except OSError as exc:
        print(f'ERROR: cannot read csv file: {exc}')
        return False
    print()
    return True


def build_insert_query():
    return (
        f'INSERT INTO {TABLE_NAME} (mars_date, temp, storm) '
        'VALUES (%s, %s, %s)'
    )


def insert_weather_rows(db_helper, weather_rows):
    insert_query = build_insert_query()
    for mars_date, temp, storm in weather_rows:
        db_helper.execute(insert_query, (mars_date, temp, storm))


def fetch_weather_rows(db_helper):
    query = (
        f'SELECT mars_date, temp, storm '
        f'FROM {TABLE_NAME} '
        'ORDER BY mars_date'
    )
    return db_helper.fetch_all(query)


def _create_blank_image(width, height, color=(255, 255, 255)):
    return [[color for _ in range(width)] for _ in range(height)]


def _set_pixel(pixels, x, y, color):
    height = len(pixels)
    width = len(pixels[0])
    if 0 <= x < width and 0 <= y < height:
        pixels[y][x] = color


def _draw_line(pixels, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = dx + dy

    while True:
        _set_pixel(pixels, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        error2 = 2 * error
        if error2 >= dy:
            error += dy
            x0 += step_x
        if error2 <= dx:
            error += dx
            y0 += step_y


def _draw_rect(pixels, left, top, right, bottom, color):
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            _set_pixel(pixels, x, y, color)


def _map_value(value, in_min, in_max, out_min, out_max):
    if in_max == in_min:
        return (out_min + out_max) // 2
    ratio = (value - in_min) / float(in_max - in_min)
    return int(out_min + ratio * (out_max - out_min))


def build_weather_chart(weather_rows):
    if not weather_rows:
        raise ValueError('no weather rows to chart')

    width = CHART_WIDTH
    height = CHART_HEIGHT
    margin = CHART_MARGIN
    pixels = _create_blank_image(width, height)

    plot_left = margin
    plot_right = width - margin
    plot_top = margin
    plot_bottom = height - margin

    temps = [row[1] for row in weather_rows]
    storms = [row[2] for row in weather_rows]
    min_temp = min(temps)
    max_temp = max(temps)
    if min_temp == max_temp:
        min_temp -= 1
        max_temp += 1
    min_storm = min(storms)
    max_storm = max(storms)
    if min_storm == max_storm:
        min_storm -= 1
        max_storm += 1

    _draw_line(pixels, plot_left, plot_top, plot_left, plot_bottom, (0, 0, 0))
    _draw_line(pixels, plot_left, plot_bottom, plot_right, plot_bottom, (0, 0, 0))

    point_count = len(weather_rows)
    previous_temp_point = None
    previous_storm_point = None
    for index, (_mars_date, temp, storm) in enumerate(weather_rows):
        x = _map_value(index, 0, point_count - 1, plot_left, plot_right)
        temp_y = _map_value(temp, min_temp, max_temp, plot_bottom, plot_top)
        storm_y = _map_value(storm, min_storm, max_storm, plot_bottom, plot_top)

        if previous_temp_point is not None:
            _draw_line(
                pixels,
                previous_temp_point[0],
                previous_temp_point[1],
                x,
                temp_y,
                (0, 102, 204),
            )
        if previous_storm_point is not None:
            _draw_line(
                pixels,
                previous_storm_point[0],
                previous_storm_point[1],
                x,
                storm_y,
                (230, 126, 34),
            )
        previous_temp_point = (x, temp_y)
        previous_storm_point = (x, storm_y)

    return pixels


def write_png(file_path, pixels):
    height = len(pixels)
    width = len(pixels[0])

    raw_rows = []
    for row in pixels:
        packed = b'\x00'
        for red, green, blue in row:
            packed += struct.pack('BBB', red, green, blue)
        raw_rows.append(packed)

    raw_data = b''.join(raw_rows)
    compressed = zlib.compress(raw_data, 9)

    def make_chunk(chunk_type, data):
        crc = zlib.crc32(chunk_type + data) & 0xffffffff
        return struct.pack('>I', len(data)) + chunk_type + data + struct.pack('>I', crc)

    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)

    try:
        with open(file_path, 'wb') as png_file:
            png_file.write(signature)
            png_file.write(make_chunk(b'IHDR', ihdr))
            png_file.write(make_chunk(b'IDAT', compressed))
            png_file.write(make_chunk(b'IEND', b''))
    except OSError as exc:
        raise OSError(f'cannot write png file: {file_path} ({exc})') from exc


def save_weather_summary_png(file_path, weather_rows):
    pixels = build_weather_chart(weather_rows)
    write_png(file_path, pixels)


def print_weather_summary(weather_rows):
    print('=== Weather summary ===')
    print(f'Total rows: {len(weather_rows)}')
    if weather_rows:
        temps = [temp for _date, temp, _storm in weather_rows]
        storms = [storm for _date, _temp, storm in weather_rows]
        print(f'Min temp: {min(temps)}')
        print(f'Max temp: {max(temps)}')
        print(f'Min storm: {min(storms)}')
        print(f'Max storm: {max(storms)}')
    print()


def main():
    csv_path = os.path.join(_script_dir(), CSV_FILENAME)
    png_path = os.path.join(_script_dir(), PNG_FILENAME)

    if not os.path.isfile(csv_path):
        print(f'ERROR: csv file not found: {csv_path}')
        print(f'Place {CSV_FILENAME} in the same folder as this script.')
        return

    if not print_csv_contents(csv_path):
        return

    try:
        weather_rows = read_mars_weather_csv(csv_path)
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}')
        return

    if not weather_rows:
        print('ERROR: no data rows found in csv file.')
        return

    print('=== Parsed CSV rows ===')
    for mars_date, temp, storm in weather_rows:
        print(f'{mars_date}, {temp}, {storm}')
    print()

    db_helper = MySQLHelper(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
    )

    try:
        db_helper.connect()
        insert_weather_rows(db_helper, weather_rows)
        print(f'Inserted {len(weather_rows)} row(s) into {TABLE_NAME}.')
        stored_rows = fetch_weather_rows(db_helper)
    except (ImportError, RuntimeError) as exc:
        print(f'ERROR: {exc}')
        return
    finally:
        db_helper.close()

    print_weather_summary(stored_rows)

    try:
        save_weather_summary_png(png_path, stored_rows)
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}')
        return

    print(f'Saved chart: {png_path}')


if __name__ == '__main__':
    main()
