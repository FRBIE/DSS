# utils/snowflake.py
import time
import threading

class Snowflake:
    def __init__(self, datacenter_id=0, worker_id=0):
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_left_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits

        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)
        self.epoch = 1609459200000  # 可自定义起始时间戳（毫秒），例如 2021-01-01

    def _time_gen(self):
        return int(time.time() * 1000)

    def _wait_until_next_millis(self, last_timestamp):
        timestamp = self._time_gen()
        while timestamp <= last_timestamp:
            timestamp = self._time_gen()
        return timestamp

    def get_id(self):
        with self.lock:
            timestamp = self._time_gen()
            if timestamp < self.last_timestamp:
                raise Exception("时钟回拨，拒绝生成ID")

            if self.last_timestamp == timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    timestamp = self._wait_until_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp
            id = ((timestamp - self.epoch) << self.timestamp_left_shift) | \
                 (self.datacenter_id << self.datacenter_id_shift) | \
                 (self.worker_id << self.worker_id_shift) | self.sequence
            return id
