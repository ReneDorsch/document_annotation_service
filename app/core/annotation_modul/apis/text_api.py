from ._base_api_ import TransformationStrategy
from ..annotation_model import DocumentAnalysis
from ..datamodels.text_models import Text


class TextStrategy(TransformationStrategy):
    """ An Agent performing all necessary tasks for the extraction and transformation of the table. """

    def __init__(self):
        super().__init__()

    def preprocess_data(self, data: DocumentAnalysis) -> None:
        chapters = {'chapters': [_.dict() for _ in data.text.chapters]}
        data.text = Text()
        data.text.read_json(chapters, data.metadata.abstract.dict())


    def postprocess_data(self, data: DocumentAnalysis) -> None:
        pass

    def process_data(self, data: DocumentAnalysis) -> None:
        """ Processes the found tables. """
        # Get the relevant pages
        pass