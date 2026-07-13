"""PortPool 端口池单元测试。"""

import pytest

from app.runtime.port_pool import PortPool


class TestPortPool:
    def test_allocate_release_cycle(self):
        """基本分配释放循环。"""
        pool = PortPool(start=8100, end=8102)
        assert pool.total_count == 3
        assert pool.available_count == 3

        p1 = pool.allocate()
        assert p1 in {8100, 8101, 8102}
        assert pool.available_count == 2

        p2 = pool.allocate()
        assert p2 != p1
        assert pool.available_count == 1

        pool.release(p1)
        assert pool.available_count == 2

        p3 = pool.allocate()
        assert pool.available_count == 1

    def test_exhaustion(self):
        """端口耗尽时抛出 RuntimeError。"""
        pool = PortPool(start=8100, end=8100)
        assert pool.total_count == 1
        pool.allocate()
        with pytest.raises(RuntimeError, match="端口池已耗尽"):
            pool.allocate()

    def test_release_out_of_range(self):
        """释放超出范围的端口不报错。"""
        pool = PortPool(start=8100, end=8101)
        pool.release(9999)  # 不在范围内，静默忽略
        assert pool.available_count == 2

    def test_invalid_range(self):
        """端口范围无效时抛出 ValueError。"""
        with pytest.raises(ValueError):
            PortPool(start=8100, end=8099)

    def test_allocate_all_then_release(self):
        """全部分配后释放，再分配应成功。"""
        pool = PortPool(start=8100, end=8102)
        ports = [pool.allocate() for _ in range(3)]
        assert pool.available_count == 0

        for p in ports:
            pool.release(p)
        assert pool.available_count == 3

        # 重新分配应该成功
        pool.allocate()
        pool.allocate()
        pool.allocate()
