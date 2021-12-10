from abc import ABC, abstractmethod

from ..annotation_model import DocumentAnalysis


class TransformationStrategy(ABC):

    @abstractmethod
    def preprocess_data(self, data: DocumentAnalysis) -> None:
        ''' Abstract method to preprocess the data in some kind. '''

    @abstractmethod
    def process_data(self, data: DocumentAnalysis) -> None:
        ''' Abstract method to process the data in some kind. '''

    @abstractmethod
    def postprocess_data(self, data: DocumentAnalysis) -> None:
        ''' Abstract method to refine the data in some kind. '''