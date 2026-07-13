"""评测 Gateway 端口池，线程安全的端口分配与回收。"""

import threading


class PortPool:
    """管理评测临时 Gateway 的端口分配，防止端口冲突。"""

    def __init__(self, start: int = 8100, end: int = 8199) -> None:
        if start > end:
            raise ValueError(f"端口范围无效: {start} > {end}")
        self._start = start
        self._end = end
        self._available: set[int] = set(range(start, end + 1))
        self._lock = threading.Lock()

    def allocate(self) -> int:
        """分配一个可用端口。端口耗尽时抛出 RuntimeError。"""
        with self._lock:
            if not self._available:
                raise RuntimeError(
                    f"评测端口池已耗尽（范围 {self._start}-{self._end}），"
                    f"请等待正在进行的评测完成后再试。"
                )
            return self._available.pop()

    def release(self, port: int) -> None:
        """释放端口回池。"""
        if port < self._start or port > self._end:
            return  # 不在管理范围内，静默忽略
        with self._lock:
            self._available.add(port)

    @property
    def available_count(self) -> int:
        """当前可用端口数。"""
        with self._lock:
            return len(self._available)

    @property
    def total_count(self) -> int:
        """端口池总容量。"""
        return self._end - self._start + 1
