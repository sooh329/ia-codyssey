import random
import time


class DummySensor:
    """테스트용 더미 환경 센서"""

    def __init__(self):
        """인스턴스를 만들고 env_values 사전 키를 준비한다"""
        self.env_values = {
            'mars_base_internal_temperature': None, # 화성 기지 내부 온도
            'mars_base_external_temperature': None, # 화성 기지 외부 온도
            'mars_base_internal_humidity': None, # 화성 기지 내부 습도
            'mars_base_external_illuminance': None, # 화성 기지 외부 광량
            'mars_base_internal_co2': None, # 화성 기지 내부 이산화탄소 농도
            'mars_base_internal_oxygen': None, # 화성 기지 내부 산소 농도
        }

    def set_env(self):
        """random으로 각 센서 범위의 값을 생성해 env_values에 채운다"""
        self.env_values['mars_base_internal_temperature'] = round(
            random.uniform(18, 30), 2
        )
        self.env_values['mars_base_external_temperature'] = round(
            random.uniform(0, 21), 2
        )
        self.env_values['mars_base_internal_humidity'] = round(
            random.uniform(50, 60), 2
        )
        self.env_values['mars_base_external_illuminance'] = round(
            random.randint(500, 715), 2
        )
        self.env_values['mars_base_internal_co2'] = round(
            random.uniform(0.02, 0.1), 4
        )
        self.env_values['mars_base_internal_oxygen'] = round(
            random.uniform(4, 7), 2
        )

    def get_env(self):
        """현재 env_values 사전을 반환한다"""
        # 측정 시각과 각 항목을 로그 파일에 남긴다
        log_path = 'mars_base_environment.log'
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        line = (
            f'{timestamp}, '
            f"{self.env_values['mars_base_internal_temperature']}, "
            f"{self.env_values['mars_base_external_temperature']}, "
            f"{self.env_values['mars_base_internal_humidity']}, "
            f"{self.env_values['mars_base_external_illuminance']}, "
            f"{self.env_values['mars_base_internal_co2']}, "
            f"{self.env_values['mars_base_internal_oxygen']}\n"
        )
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(line)

        return self.env_values


# DummySensor를 ds 인스턴스로 만들고 set_env, get_env를 차례로 호출해 값을 확인한다
ds = DummySensor()
ds.set_env()
print(ds.get_env())
