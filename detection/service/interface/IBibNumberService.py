from abc import abstractmethod


class IBibNumberService:
    @abstractmethod
    def get_all_numbers(self)->list[int]:
        pass

    @abstractmethod
    def find_number(self, number:int)->int|None:
        pass

    @abstractmethod
    def contains_number(self, number) -> bool:
        pass