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


def read_setting_lines(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            raw_lines = file.readlines()
    except Exception:
        return []

    lines = []
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        lines.append(line)
    return lines


def parse_output_settings(lines):
    settings = {
        'info': set(),
        'load': set(),
    }

    for line in lines:
        if line.startswith('info.'):
            settings['info'].add(line[5:])
            continue
        if line.startswith('load.'):
            settings['load'].add(line[5:])
            continue
        settings['info'].add(line)
        settings['load'].add(line)

    return settings


def apply_output_filter(payload, allowed_keys):
    if not allowed_keys:
        return payload

    filtered = {}
    for key in allowed_keys:
        if key in payload:
            filtered[key] = payload[key]
    return filtered


class MissionComputer:
    def __init__(self):
        self._settings_path = 'setting.txt'
        self._settings = parse_output_settings(read_setting_lines(self._settings_path))

    def _print_json(self, kind, payload):
        payload = apply_output_filter(payload, self._settings.get(kind, set()))
        print(dict_to_json(payload), flush=True)
        return payload

    def _get_system_info_raw(self):
        info = {
            'operating_system': None,
            'operating_system_version': None,
            'cpu_type': None,
            'cpu_cores': None,
            'memory_size_bytes': None,
        }

        try:
            import platform

            info['operating_system'] = platform.system()
            info['operating_system_version'] = platform.version()

            cpu_type = platform.processor()
            if not cpu_type:
                cpu_type = platform.machine()
            info['cpu_type'] = cpu_type
        except Exception:
            pass

        try:
            import os

            info['cpu_cores'] = os.cpu_count()
        except Exception:
            pass

        memory_total, _ = self._get_windows_memory_status()
        if memory_total is None:
            memory_total = self._get_total_memory_bytes_unix()
        if memory_total is not None:
            info['memory_size_bytes'] = int(memory_total)

        return info

    def _get_windows_memory_status(self):
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            if not ok:
                return None, None
            return int(status.ullTotalPhys), float(status.dwMemoryLoad)
        except Exception:
            return None, None

    def _get_total_memory_bytes_unix(self):
        try:
            import os

            if hasattr(os, 'sysconf'):
                page_size = os.sysconf('SC_PAGE_SIZE')
                phys_pages = os.sysconf('SC_PHYS_PAGES')
                if isinstance(page_size, int) and isinstance(phys_pages, int):
                    return int(page_size * phys_pages)
        except Exception:
            return None

        return None

    def get_mission_computer_info(self):
        return self._print_json('info', self._get_system_info_raw())

    def _get_load_raw(self):
        payload = {
            'cpu_usage_percent': None,
            'memory_usage_percent': None,
        }

        cpu_percent = self._get_cpu_usage_percent()
        if cpu_percent is not None:
            payload['cpu_usage_percent'] = round(float(cpu_percent), 2)

        mem_percent = self._get_memory_usage_percent()
        if mem_percent is not None:
            payload['memory_usage_percent'] = round(float(mem_percent), 2)

        return payload

    def _get_cpu_usage_percent(self):
        cpu = self._get_cpu_usage_percent_windows()
        if cpu is not None:
            return cpu

        cpu = self._get_cpu_usage_percent_unix()
        if cpu is not None:
            return cpu

        return None

    def _get_cpu_usage_percent_windows(self):
        try:
            import ctypes

            class FileTime(ctypes.Structure):
                _fields_ = [
                    ('dwLowDateTime', ctypes.c_uint32),
                    ('dwHighDateTime', ctypes.c_uint32),
                ]

            def to_int64(ft):
                return (int(ft.dwHighDateTime) << 32) | int(ft.dwLowDateTime)

            idle1 = FileTime()
            kernel1 = FileTime()
            user1 = FileTime()
            ok1 = ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1)
            )
            if not ok1:
                return None

            time.sleep(0.1)

            idle2 = FileTime()
            kernel2 = FileTime()
            user2 = FileTime()
            ok2 = ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2)
            )
            if not ok2:
                return None

            idle_delta = to_int64(idle2) - to_int64(idle1)
            kernel_delta = to_int64(kernel2) - to_int64(kernel1)
            user_delta = to_int64(user2) - to_int64(user1)

            total = kernel_delta + user_delta
            if total <= 0:
                return None

            busy = total - idle_delta
            percent = (busy / total) * 100
            if percent < 0:
                percent = 0
            if percent > 100:
                percent = 100
            return percent
        except Exception:
            return None

    def _get_cpu_usage_percent_unix(self):
        try:
            import os

            if not hasattr(os, 'getloadavg'):
                return None

            load1, _, _ = os.getloadavg()
            cores = os.cpu_count() or 1
            percent = (float(load1) / float(cores)) * 100
            if percent < 0:
                percent = 0
            return percent
        except Exception:
            return None

    def _get_memory_usage_percent(self):
        _, mem = self._get_windows_memory_status()
        if mem is not None:
            return mem

        mem = self._get_memory_usage_percent_linux_proc()
        if mem is not None:
            return mem

        return None

    def _get_memory_usage_percent_linux_proc(self):
        try:
            with open('/proc/meminfo', 'r', encoding='utf-8') as file:
                lines = file.readlines()
        except Exception:
            return None

        total_kb = None
        available_kb = None

        for raw in lines:
            line = raw.strip()
            if line.startswith('MemTotal:'):
                parts = line.split()
                if len(parts) >= 2:
                    total_kb = int(parts[1])
            elif line.startswith('MemAvailable:'):
                parts = line.split()
                if len(parts) >= 2:
                    available_kb = int(parts[1])

        if total_kb is None or available_kb is None or total_kb <= 0:
            return None

        used_kb = total_kb - available_kb
        return (used_kb / total_kb) * 100

    def get_mission_computer_load(self):
        return self._print_json('load', self._get_load_raw())


if __name__ == '__main__':
    runComputer = MissionComputer()
    runComputer.get_mission_computer_info()
    runComputer.get_mission_computer_load()

