from collections import defaultdict
from typing import List
import json
from app.core.config import ANNOTATION_INPUT_PARAMETERS
import app.core.schemas.datamodel as io

class Annotation:
    with open(ANNOTATION_INPUT_PARAMETERS) as file:
        ANNOTATION_SPECIFICATION = json.load(file)
    IDCOUNTER = 1

    def __init__(self, label: str, startPos: int, endPos: int, category: str, specificCategory: str, confidence:
    float, typeOfAnnotation: bool, tokens, wordList):
        self.label: str = label
        self.startPos: int = startPos
        self.endPos: int = endPos
        self.confidence: float = confidence
        self.annotationID: int = Annotation.IDCOUNTER
        self.category: str = category
        self.specificCategory: str = specificCategory
        self.wordList: List['Word'] = []
        self.synonymicalAnnotations: List['Annotation'] = []
        self.typeOfAnnotation = typeOfAnnotation
        self.setWords(tokens, wordList, typeOfAnnotation)
        self.knowledgeObject = None
        self.textualPatternMatch = False
        self.numericMatch = False

        Annotation.IDCOUNTER += 1

    def to_io(self) -> io.Annotation:
        return io.Annotation(**{
            'words': [_.to_io() for _ in self.wordList],
            'category': self.category,
            'id': self.annotationID,
        })
    def saveAsDict(self):
        res = {
            'id': self.annotationID,
            'category': self.category,
            'label': self.label,
            'words': [_.id for _ in self.wordList]
        }
        return res

    def saveAsDictSmall(self):
        return self.annotationID

    def getWordsAsString(self, useNormalizedForm=False) -> str:
        words = ""
        for word in self.wordList:
            if useNormalizedForm:
                if word.has_space_after_word:
                    words += word.normalized_form + " "
                else:
                    words += word.normalized_form
            else:
                if word.has_space_after_word:
                    words += word.word + " "
                else:
                    words += word.word
        return words.rstrip()

    @classmethod
    def create_model_annotation(cls, span, wordList):
        return cls(span.text, span.start_pos, span.end_pos, span.tag, span.tag, span.score, True, span.tokens, wordList)

    @classmethod
    def create_manual_annotation(cls, label: str, startPos: int, endPos: int, category: str,
                                 specificCategory: str, tokens):
        return cls(label, startPos, endPos, category, specificCategory, 1.0, False, tokens, None)

    def setWords(self, tokens, wordList: List['Word'], typeOfAnnotation: bool = True):
        '''
        Adds the Words to the Annotation and the Annotation to the Words
        :param tokens:
        :param wordList:
        :param typeOfAnnotation: True if Annotated with Model, False if Annotated with Manual
        :return:
        '''
        # is Annotation with Model
        if typeOfAnnotation:
            for token in tokens:
                for word in wordList:
                    if word.start_pos == token.start_pos:
                        if word.start_pos not in [_.start_pos for _ in self.wordList]:
                            self.wordList.append(word)
                            word.add_annotation(token.get_tag('ner'), self, typeOfAnnotation)
        else:
            # Is Annotation with Manual Annotater
            self.wordList.extend(tokens)
            for word in tokens:
                word.add_annotation(self.category, self, typeOfAnnotation)

    def addSynonym(self, synonym: 'Annotation', state: bool = True):
        '''
        Adds the Synonym (inclusive Acronyms) to the Annotation.
        :param synonym: Synonymical Annotation of the Annotation
        :param state: Limits the recursive call of the Function
        :return:
        '''
        self.synonymicalAnnotations.append(synonym)
        if state: synonym.addSynonym(self, False)

    def adjustInformation(self):
        if self.synonymicalAnnotations != []:
            zwerg = defaultdict(int)
            for anno in self.synonymicalAnnotations:
                zwerg[anno.category] += 1
            self.category = max([(_, __) for _, __ in zwerg.items()], key=lambda x: x[1])[0]
            zwerg = defaultdict(int)
            for anno in self.synonymicalAnnotations:
                zwerg[anno.specificCategory] += 1
            self.specificCategory = max([(_, __) for _, __ in zwerg.items()], key=lambda x: x[1])[0]
