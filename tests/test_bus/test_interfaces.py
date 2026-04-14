"""Unit tests for IBusDriver abstract interface."""

import pytest

from ai_driven_development_labs.bus.interfaces import IBusDriver


class TestIBusDriverABC:
    """IBusDriver ABC のテスト。"""

    def test_cannot_instantiate_directly(self):
        """IBusDriver を直接インスタンス化すると TypeError が発生することを確認する。"""
        with pytest.raises(TypeError):
            IBusDriver()  # type: ignore[abstract]

    def test_concrete_without_all_methods_raises(self):
        """抽象メソッドを一部しか実装しない具象クラスは TypeError になることを確認する。"""

        class PartialBusDriver(IBusDriver):
            def open(self) -> None:
                pass

            # close, read_register, write_register, transfer は未実装

        with pytest.raises(TypeError):
            PartialBusDriver()  # type: ignore[abstract]

    def test_concrete_full_implementation(self):
        """すべての抽象メソッドを実装した具象クラスはインスタンス化できることを確認する。"""

        class ConcreteBusDriver(IBusDriver):
            def open(self) -> None:
                pass

            def close(self) -> None:
                pass

            def read_register(self, register: int, length: int) -> bytes:
                return bytes(length)

            def write_register(self, register: int, data: bytes) -> None:
                pass

            def transfer(self, data: bytes) -> bytes:
                return data

        bus = ConcreteBusDriver()
        assert isinstance(bus, IBusDriver)

    def test_abstract_methods_list(self):
        """IBusDriver が期待する抽象メソッドをすべて持つことを確認する。"""
        expected = {"open", "close", "read_register", "write_register", "transfer"}
        assert IBusDriver.__abstractmethods__ == expected
