from abc import ABC, abstractmethod


class BaseConnector(ABC):

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def test_connection(self):
        pass

    @abstractmethod
    def fetch_data(self):
        pass

    @abstractmethod
    def transform_data(self):
        pass

    @abstractmethod
    def sync(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass