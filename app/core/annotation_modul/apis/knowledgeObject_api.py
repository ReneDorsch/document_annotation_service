from ._base_api_ import TransformationStrategy
from ..annotation_model import DocumentAnalysis
from ..datamodels.annotation_model import Annotation
from ..datamodels.knowledge_object_model import KnowledgeObject
import copy
from typing import List
class KnowledgeObjectStrategy(TransformationStrategy):

    def preprocess_data(self, data: DocumentAnalysis) -> None:
        pass

    def postprocess_data(self, data: DocumentAnalysis) -> None:
        pass

    def process_data(self, data: DocumentAnalysis) -> None:

        def helper_function():
            res = []
            words = []
            annotations = data.annotations
            for annotation in annotations:
                already_annotated = False
                for word in annotation.wordList:
                    if word in words:
                        already_annotated = True
                if already_annotated:
                    continue
                words.extend(annotation.wordList)
                res.append(annotation)
            return res

        annotations = helper_function()
        zwerg = copy.copy(annotations)

        # self.adjustCategories(annotations)
        kObjs = self.get_knowledgeObjects_for_text(zwerg)

        data.knowledgeObjects = kObjs
        kObjs = self.get_knowledgeObjects_for_tables(data)

    def get_knowledgeObjects_for_text(self, annotations):
        res = []
        while annotations:
            annotation: Annotation = annotations.pop(0)
            annotation.adjustInformation()
            knowObj = KnowledgeObject(annotation)
            listOfAnnotationToRemove = knowObj.add_additional_annotations(annotations)

            annotation.adjustInformation()
            annotations = [_ for _ in annotations if _ not in listOfAnnotationToRemove]
            res.append(knowObj)
        return res

    def get_knowledgeObjects_for_tables(self, data) -> List[KnowledgeObject]:
        res = []
        for table in data.tables:
            res.extend(table.annotate_cells())
        return res
