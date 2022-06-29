from detection.service.interface.IBibNumberService import IBibNumberService


class MockBibNumberService(IBibNumberService):
    def __init__(self):
        self.numbers = list(range(1, 999))

    def get_all_numbers(self) -> list[int]:
        return self.numbers

    def find_number(self, number: int) -> int | None:
        return number if number in self.numbers else None

    def contains_number(self, number) -> bool:
        return number in self.numbers