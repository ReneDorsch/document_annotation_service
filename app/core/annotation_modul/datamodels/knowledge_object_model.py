from fuzzywuzzy import process, fuzz
import regex
from typing import List
from .annotation_model import Annotation
import app.core.schemas.datamodel as io

class KnowledgeObject:
    IDCounter = 1

    def __init__(self, annotation: Annotation):
        self.annotations: List[Annotation] = self._get_annotations_from_annotation_object(annotation)
        self.knowObjID = KnowledgeObject.IDCounter
        self.labels: List[str] = [_.label for _ in self.annotations]
        self.category: str = annotation.category
        self.specificCategory: str = annotation.specificCategory
        self._labels_normalized: List[str] = [" ".join([word.normalized_form for word in annotation.wordList]) for annotation in self.annotations]
        KnowledgeObject.IDCounter += 1

    def to_io(self) -> io.KnowledgeObject:
        return io.KnowledgeObject(**{
            'id': self.knowObjID,
            'labels': [_ for _ in self.labels],
            'category': self.category,
            'annotation_ids': [_.annotationID for _ in self.annotations]
        })

    def saveAsDictSmall(self):
        return self.knowObjID

    def save_as_dict(self):
        res = {
           'id': self.knowObjID,
           'category': self.specificCategory,
           'labels': self.labels
               }
        return res

    def _get_annotations_from_annotation_object(self, annotation: Annotation) -> List[Annotation]:
        annos = [annotation]
        annos.extend(annotation.synonymicalAnnotations)
        [self._add_knowledge_object_to_annotation(anno) for anno in annos]
        return annos

    def _add_knowledge_object_to_annotation(self, annotation):
        annotation.knowledgeObject = self

    def add_additional_annotations(self, annotations: List[Annotation]) -> List[Annotation]:
        '''
        Adds other annotation to the found Annotation if these are similiar enough.
        :param annotations:
        :return:
        '''
        annotationsToDelete = []
        while True:
            counter = 0
            for annotation in annotations:
                if self._annotation_is_part_of_knowledgeObject_fuzzy_wuzzy_combined_with_exact(annotation): # and \
                        #self._category_is_part_of_knowledgeObject(annotation):
                    self.addAnnotation(annotation)
                    annotationsToDelete.append(annotation)
                    annotations.remove(annotation)
                    counter += 1

            if counter == 0:
                break
        return annotationsToDelete

    def _category_is_part_of_knowledgeObject(self, annotation: Annotation) -> bool:
        '''

        :param annotation:
        :return:
        '''
        return self.category == annotation.category

    def _annotation_is_part_of_knowledgeObject(self, annotation: Annotation) -> bool:
        '''

        :param annotation:
        :return:
        '''

        normalized_annotation = " ".join(word.normalized_form for word in annotation.wordList)
        if normalized_annotation in self._labels_normalized:
            return True
        if len(annotation.synonymicalAnnotations) > 0:
            for synonymAnnotation in annotation.synonymicalAnnotations:
                normalized_annotation = " ".join(word.normalized_form for word in synonymAnnotation.wordList)
                if normalized_annotation in self._labels_normalized:
                    return True
        return False


    def _label_is_part_of_knowledgeObject_fuzzy_wuzzy(self, annotation: Annotation):
        '''

        :param annotation:
        :return:
        '''
        normalized_kObj_labels = [_.lower() for _ in self._labels_normalized]
        normalized_word = " ".join([word.normalized_form for word in annotation.wordList])
        results = process.extract(normalized_word, normalized_kObj_labels, scorer=fuzz.token_set_ratio)

        highestConfidenceOfResult = results[0][1]
        if highestConfidenceOfResult >= 90:
            return True
        if len(annotation.synonymicalAnnotations) > 0:
            for synonymAnnotation in annotation.synonymicalAnnotations:
                normalized_synonym = " ".join([word.normalized_form for word in synonymAnnotation.wordList])
                results = process.extract(normalized_synonym, normalized_kObj_labels, scorer=fuzz.token_set_ratio)
                highestConfidenceOfResult = results[0][1]
                if highestConfidenceOfResult >= 90:
                    return True
        return False

    def _annotation_is_part_of_knowledgeObject_fuzzy_wuzzy_combined_with_exact(self, annotation: Annotation):
        '''

        :param annotation:
        :return:
        '''
        if self.containsNumber(annotation):
            return self._annotation_is_part_of_knowledgeObject(annotation)
        elif len(annotation.label) < 4:
            return self._annotation_is_part_of_knowledgeObject(annotation)
        else:
            return self._label_is_part_of_knowledgeObject_fuzzy_wuzzy(annotation)
        return False

    def containsNumber(self, annotation: Annotation):
        '''
        Some Rules to check if the string is a number
        :param label:
        :return:
        '''
        regexDigit = ' \d+(,\d+|) '
        words_in_label = [word.normalized_form for word in annotation.wordList]
        # If a single Word is a Number
        for word in words_in_label:
            if regex.search(regexDigit, " " + word + " "):
                return True
        return False

    def annotationIsPartOfKnowledgeObjectFuzzy(self, annotation: Annotation):
        '''

        :param annotation:
        :return:
        '''

        for searchTerm in self.labels:
            label = annotation.label.lower()
            numberOfErrors = str(int((len(label) / 4)))
            regexPattern = r"(%s){e<=%s:[\D]}" % (label, numberOfErrors)
            if regex.fullmatch(regexPattern, searchTerm.lower()) is not None:
                return True
        if len(annotation.synonymicalAnnotations) > 0:
            for synonymAnnotation in annotation.synonymicalAnnotations:
                for searchTerm in self.labels:
                    label = synonymAnnotation.label.lower()
                    numberOfErrors = str(int((len(label) / 4)))
                    regexPattern = r"(%s){e<=%s:[\D]}" % (label, numberOfErrors)
                    if regex.fullmatch(regexPattern, searchTerm.lower()) is not None:
                        return True
        return False

    def addAnnotation(self, annotation: Annotation):
        if annotation not in self.annotations:
            self.annotations.append(annotation)
            self._add_knowledge_object_to_annotation(annotation)
            self.setLabels()
        if len(annotation.synonymicalAnnotations) > 0:
            for synonymAnnotation in annotation.synonymicalAnnotations:
                if synonymAnnotation not in self.annotations:
                    self.annotations.append(synonymAnnotation)
                    self._add_knowledge_object_to_annotation(synonymAnnotation)
                    self.setLabels()

    def setLabels(self):
        for annotation in self.annotations:
            normalized_label = " ".join([_.normalized_form for _ in annotation.wordList])
            if annotation.label not in self.labels:
                self.labels.append(annotation.label)
            if normalized_label not in self._labels_normalized:
                self._labels_normalized.append(normalized_label)
            for synonym in annotation.synonymicalAnnotations:
                normalized_label = " ".join([_.normalized_form for _ in synonym.wordList])
                if synonym.label not in self.labels:
                    self.labels.append(synonym.label)
                if normalized_label not in self._labels_normalized:
                    self._labels_normalized.append(normalized_label)
