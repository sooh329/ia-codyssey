import time


def dict_to_json(data):
    items = []
    for key in sorted(data.keys()):
        value = data[key]
        if value is None:
            rendered = 'null'
        elif isinstance(value, bool):
            rendered = 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            rendered = str(value)
        else:
            rendered = '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'

        items.append(f'  "{key}": {rendered}')

    return '{\n' + ',\n'.join(items) + '\n}'


class DummySensor:
    """테스트용 더미 환경 센서

    제약사항(추가 import 금지)을 지키기 위해 표준 random 모듈 대신
    time 기반 의사난수를 사용한다.
    """

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': None,
            'mars_base_external_temperature': None,
            'mars_base_internal_humidity': None,
            'mars_base_external_illuminance': None,
            'mars_base_internal_co2': None,
            'mars_base_internal_oxygen': None,
        }
        self._seed = int(time.time() * 1000) & 0xFFFFFFFF

    def _rand_u32(self):
        self._seed = (1664525 * self._seed + 1013904223) & 0xFFFFFFFF
        return self._seed

    def _rand01(self):
        return self._rand_u32() / 4294967296

    def _rand_float(self, low, high):
        return low + (high - low) * self._rand01()

    def _rand_int(self, low, high):
        if high < low:
            low, high = high, low
        span = high - low + 1
        return low + (self._rand_u32() % span)

    def set_env(self):
        self.env_values['mars_base_internal_temperature'] = round(
            self._rand_float(18, 30), 2
        )
        self.env_values['mars_base_external_temperature'] = round(
            self._rand_float(0, 21), 2
        )
        self.env_values['mars_base_internal_humidity'] = round(
            self._rand_float(50, 60), 2
        )
        self.env_values['mars_base_external_illuminance'] = round(
            float(self._rand_int(500, 715)), 2
        )
        self.env_values['mars_base_internal_co2'] = round(
            self._rand_float(0.02, 0.1), 4
        )
        self.env_values['mars_base_internal_oxygen'] = round(
            self._rand_float(4, 7), 2
        )

    def get_env(self):
        return self.env_values


class MissionComputer:
    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': None,
            'mars_base_external_temperature': None,
            'mars_base_internal_humidity': None,
            'mars_base_external_illuminance': None,
            'mars_base_internal_co2': None,
            'mars_base_internal_oxygen': None,
        }
        self.ds = DummySensor()

        self._avg_sum = {key: 0.0 for key in self.env_values.keys()}
        self._avg_count = 0
        self._avg_window_start = time.time()

    def _update_averages(self, current):
        for key, value in current.items():
            if isinstance(value, (int, float)):
                self._avg_sum[key] += float(value)

        self._avg_count += 1

    def _maybe_print_5min_average(self):
        now = time.time()
        if now - self._avg_window_start < 300:
            return

        if self._avg_count <= 0:
            self._avg_window_start = now
            return

        avg_values = {}
        for key in self.env_values.keys():
            avg_values[key] = round(self._avg_sum[key] / self._avg_count, 4)

        payload = {
            'type': '5min_average',
            'samples': self._avg_count,
            'values': avg_values,
        }
        print(dict_to_json(payload), flush=True)

        self._avg_sum = {key: 0.0 for key in self.env_values.keys()}
        self._avg_count = 0
        self._avg_window_start = now

    def get_sensor_data(self):
        try:
            import msvcrt  # 보너스(키 입력 중지)용: Windows 표준 라이브러리
        except Exception:
            msvcrt = None

        while True:
            if msvcrt is not None and msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'q', b'Q', b'\x1b'):
                    print('Sytem stoped....', flush=True)
                    return

            self.ds.set_env()
            current = self.ds.get_env()
            for key in self.env_values.keys():
                self.env_values[key] = current.get(key)

            print(dict_to_json(self.env_values), flush=True)

            self._update_averages(self.env_values)
            self._maybe_print_5min_average()

            time.sleep(5)


if __name__ == '__main__':
    RunComputer = MissionComputer()
    RunComputer.get_sensor_data()
