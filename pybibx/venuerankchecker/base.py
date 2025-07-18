from abc import ABC, abstractmethod

class BaseSource(ABC):
    def __init__(self, data_by_year):
        self.data_by_year = data_by_year

    @abstractmethod
    def check(self, venue_name, log=True):
        pass

    @abstractmethod
    def available_years(self):
        pass
