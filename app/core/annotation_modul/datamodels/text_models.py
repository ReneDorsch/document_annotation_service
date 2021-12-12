from __future__ import annotations
from typing import List, Tuple, Dict

from .annotation_model import Annotation
from app.core.config import ABBREVIATIONS
import json
from app.core.annotation_modul.apis.util_functions import STEMMER, TOKENIZER
import app.core.schemas.datamodel as io
import re

class Text:
    def __init__(self):
        self.chapters = []
        self.abstract = None
        self.annotations = []
        self.knowledgeObjects = []
        self.tables = []

    def to_io(self) -> io.Text:
        return io.Text(**{
            'chapters': [_.to_io() for _ in self.chapters],
            'abstract': self.abstract.to_io() if self.abstract is not None else None
        })
    def read_json(self, jsonDumpText, jsonDumpAbstract):
        self.chapters = [Chapter(chap) for chap in jsonDumpText['chapters']]
        if jsonDumpAbstract is not None:
            self.abstract = self._set_abstract(jsonDumpAbstract)



    def _set_abstract(self, dumpfile):
        if 'paragraphs' in dumpfile:
            return Chapter(dumpfile)
        else:
            return None


class Chapter:

    def __init__(self, jsonDump):
        self.paragraphs = [Paragraph(para) for para in jsonDump['paragraphs']]

    def to_io(self) -> io.Chapter:
        return io.Chapter(**{
            'paragraphs': [_.to_io() for _ in self.paragraphs]
        })

    def save_as_dict(self):
        annotations = self.getAnnotations()
        knowledgeObjects = self.getKnowledgeObjects()
        res = {
            "paragraphs": [_.save_as_dict() for _ in self.paragraphs],
            "knowledgeObject_references": [_.saveAsDictSmall() for _ in knowledgeObjects]
        }
        return res

    def getAnnotations(self):

        res = []
        for _ in self.paragraphs:
            annotations = _.getAnnotations()
            res.extend(annotations)
        return res
        # res = []
        # res.extend([_.getAnnotations() for _ in self.paragraphs])
        # return res

    def getKnowledgeObjects(self):
        res = []
        for _ in self.paragraphs:
            kObjs = _.getKnowledgeObjects()
            res.extend(kObjs)
        return list(set(res))
        # res = []
        # res.extend([_.setKnowledgeObjects() for _ in self.paragraphs])
        # return list(set(res))


class Paragraph:

    def __init__(self, jsonDump):
        self.sentences = [Sentence(sent, self) for sent in jsonDump['sentences']]

    def to_io(self) -> io.Paragraph:
        return io.Paragraph(**{
            'sentences': [_.to_io() for _ in self.sentences]
        })

    def save_as_dict(self):
        annotations = self.getAnnotations()
        knowledgeObjects = self.getKnowledgeObjects()
        res = {
            'sentences': [_.save_as_dict() for _ in self.sentences],
            "knowledgeObject_references": [_.saveAsDictSmall() for _ in knowledgeObjects]
        }
        return res

    def getAnnotations(self):
        res = []
        for _ in self.sentences:
            annotations = _.getAnnotations()
            res.extend(annotations)
        return res

    def getKnowledgeObjects(self):
        res = []
        for _ in self.sentences:
            kObjs = _.getKnowledgeObjects()
            res.extend(kObjs)
        return list(set(res))


class Sentence:
    ID = 0

    def __init__(self, jsonDump: Dict, paragraph):
        self.id = Sentence.ID
        self.text_in_sentence: str = jsonDump['text'] if 'text' in jsonDump else jsonDump['sentence']
        self.paragraph = paragraph
        self.words: List[Word] = []
        self.annotations: List[Annotation] = []
        Sentence.ID += 1
        self.setWords()

    def to_io(self) -> io.Sentence:
        return io.Sentence(**{
            'words': [_.to_io() for _ in self.words]
        })

    @classmethod
    def from_table(cls, sentence, table) -> Sentence:
        zwerg = {'sentence': sentence,
                 'paragraph_id': Sentence.ID}
        sentence = cls(zwerg, table)
        sentence.setWords()
        return sentence

    def getText(self, useNormalizedForm: bool = False):
        if useNormalizedForm:
            return self.getSentenceInNormalform()
        return self.text_in_sentence

    def getSentenceInNormalform(self):
        sentence = ""
        for word in self.words:
            if word.has_space_after_word:
                sentence += word.normalized_form + " "
            else:
                sentence += word.normalized_form
        return sentence

    def save_as_dict(self):
        annotations = self.getAnnotations()
        knowledgeObjects = self.getKnowledgeObjects()
        # print(self.text_in_sentence)
        res = {
            'words': [_.save_as_dict() for _ in self.words],
            "knowledgeObject_references": [_.saveAsDictSmall() for _ in knowledgeObjects]
        }
        return res

    def getAnnotations(self) -> List[Annotation]:
        return [_.annotation for _ in self.words if _.has_annotation]

    def getKnowledgeObjects(self) -> List['KnowledgeObject']:
        annotations = self.getAnnotations()
        return list(set([_.knowledgeObject for _ in annotations]))

    def setWords(self) -> None:
        '''
        Splits the sentence in Words and save the words in the parameter words
        :return: None
        '''
        if len(self.words) > 0:
            return

        tokens = TOKENIZER.tokenize(self.text_in_sentence)
        # Create a Object for each Word
        prevWord: Word = None
        for token in tokens:
            word = Word(token.text, token.start_pos, token.end_pos, prevWord, token.whitespace_after)
            self.words.append(word)
            prevWord = word

    def get_words_of_span(self, span: Tuple[int, int], useNormalizedForm: bool = False) -> List[Word]:
        if useNormalizedForm:
            return self._get_normalized_words_of_span(span)
        else:
            return self._get_words_of_span(span)

    def _get_normalized_words_of_span(self, span: Tuple[int, int]):
        listOfWords = []
        startPosSpan = span[0]
        endPosSpan = span[1]
        startPosWord = 0
        endPosWord = 0
        for word in self.words:
            startPosWord = endPosWord
            wordLength = len(word.normalized_form)
            if word.has_space_after_word:
                endPosWord = (startPosWord + wordLength + 1)
            else:
                endPosWord = (startPosWord + wordLength)
            if startPosWord <= startPosSpan < endPosWord:
                listOfWords.append(word)
            elif startPosSpan < startPosWord < endPosSpan:
                listOfWords.append(word)
            elif startPosWord < endPosSpan < endPosWord:
                listOfWords.append(word)

        return listOfWords

    def _get_words_of_span(self, span: Tuple[int, int]):
        #####
        # A span is a list of words that is defined by its start and endposition
        # E.g.
        # Apple AG -> is defined by the startPosition (0) and the endposition (7)
        # A new company was bought by Apple AG.
        #                             |      |
        #
        listOfWords = []
        startPos = span[0]
        endPos = span[1]
        for word in self.words:
            if startPos <= word.start_pos and word.end_pos <= endPos:
                listOfWords.append(word)
            elif word.start_pos <= startPos and endPos <= word.end_pos:
                listOfWords.append(word)
        return listOfWords


class Word:
    IDCounter = 0
    LONGFORMS = None
    with open(ABBREVIATIONS, mode="rb") as js:
        LONGFORMS = json.load(js)

    def __init__(self, word, startPos: int, endPos: int, prevWord: Word, spaceAfterWord: bool = False):
        self.id = Word.IDCounter
        self.word = word
        self.long_form = word
        if word in Word.LONGFORMS.keys():
            self.long_form = Word.LONGFORMS[word]
        self.normalized_form: str = self._normalize_word(word)
        self.has_annotation = False
        self.annotation: Annotation = None
        self.start_pos: int = startPos
        self.end_pos: int = endPos
        self.tag_name = ""
        self.previous_word: Word = prevWord
        self.has_space_after_word = spaceAfterWord
        self.next_word: Word = None
        if self.previous_word:
            self.previous_word.next_word = self

        Word.IDCounter += 1

    def to_io(self) -> io.Word:
        return io.Word(**{
            'id': self.id,
            'prev_word_id': self.previous_word.id if self.previous_word is not None else -1,
            'text': self.word,
            'normalized_text': self.normalized_form,
            'enriched_text': self.long_form,
            'annotation_id': self.annotation.annotationID if self.annotation is not None else -1,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos
        })

    def _normalize_word(self, word: str) -> str:
        #######
        # For the normalization we have to consider serveral parts
        # We have to distinguish between numerical word and textual word
        # If we have a numerical value it can come in serveral forms
        # E.g
        # 0.80 == 0.8       <-- first example
        # 0.80 == 0,80      <-- third example
        # If we have a textual word we have also different forms
        # E.g.
        # 0.80 GPa == 0.80 gpa        <-- fourth example
        # 0.80 GPa == 0.80 gigapascal <-- fifth example
        # In addtion we also have to consider different types of format
        # E.g.
        # +/- == ±
        # , == . (In some cases)
        # – == -
        # To further normalize the words we will stem the words
        # Stemming is a process to reduce a textual word to its root
        # E.g
        # editing -> edit

        # First check if its a numerical value
        potential_numerical_value = re.sub('(,|\.)', '', word)
        if potential_numerical_value.isdigit():
            word = re.sub('\.', ',', word)
            if re.search('\d+,\d*0 ', word + " "):
                word = re.sub('^0', '', word[::-1])
                word = word[::-1]
                if word[-1] == ',':
                    word = word[-1]
        # Check the texutal representation and normalize it
        else:
            if self.long_form != self.word:
                word = self.long_form
            word = re.sub("[–|-|\\|\|\+/\-|±) ]+", "", word.lower())
            word = STEMMER.stemWord(word)
        return word

    def save_as_dict(self):
        # To DO: Chage so it will always have kObj and previous_word in the file
        res = {
            'id': self.id,
            'word': self.word,
            'normalized_word': self.normalized_form,
            'longform_word': self.long_form,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'whitespace_after_word': self.has_space_after_word
        }
        if self.previous_word is not None:
            res['prev_word'] = self.previous_word.id
        if self.annotation:
            res['knowledgeObject_reference'] = self.annotation.knowledgeObject.knowObjID
        return res

    def add_annotation(self, tagName: str, annotation: Annotation, annotationType: bool):
        self.has_annotation = True
        self.tag_name = tagName
        self.annotation = annotation
        if annotationType == True:
            self.annotationType = "Model"
        else:
            self.annotationType = "Manual"
