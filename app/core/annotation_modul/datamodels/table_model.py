from __future__ import annotations
import re

from typing import Tuple, List, Dict, Union

from app.core.annotation_modul.datamodels.text_models import Sentence
from app.core.annotation_modul.datamodels.annotation_model import Annotation

from app.core.config import CATEGORICAL_LABELS, UNITS
from ..apis.util_functions import load_table
import app.core.schemas.datamodel as io

from ..apis.util_functions import TOKENIZER
from flair.data import Sentence as fdSentence


class Table:
    # Get the categories and units as a sorted list
    CATEGORICAL_LABELS = load_table(CATEGORICAL_LABELS)
    UNITS = load_table(UNITS)

    def __init__(self, jsonDump: Dict):
        t_header = jsonDump['table_header']
        if t_header['type'] == "row":
            t_header = Row(t_header)
        else:
            t_header = Column(t_header)
        self.table_header: Union[Row, Column] = t_header
        self.rows = [Row(rowDump) for rowDump in jsonDump['rows']]
        self.cols = [Column(colDump) for colDump in jsonDump['columns']]
        self.units = None
        self.references = None
        self.labels = []
        self.data = []
        self.lines = []
        self.textual_representations: List[Sentence] = []

    def to_io(self) -> io.Table:
        return io.Table(**{
            'rows': [_.to_io() for _ in self.rows],
            'columns': [_.to_io() for _ in self.cols],
            'data': [_.to_io() for _ in self.lines],
            'table_header': self.table_header.to_io(),
            'units': self.units
        })

    def get_table_header(self) -> Union[Row, Column]:
        return self.table_header

    def annotate_cells(self):
        res = []
        cells = []
        annotations = []

        for sentence in self.textual_representations:
            annotations.extend(sentence.annotations)
        annotations = list(set(annotations))

        lines = self.lines + [self.table_header]
        for line in lines:
            cells.extend(line.cells)

        for annotation in annotations:
            for cell in cells:
                sentence = fdSentence(cell.textInCell, use_tokenizer=TOKENIZER)
                for word in sentence.tokens:
                    for annotation_word in annotation.wordList:
                        if word.text == annotation_word.word:
                            cell.annotations.append(annotation)
                            cell.knowledgeObject.append(annotation.knowledgeObject)
                            res.append(annotation.knowledgeObject)
        return res


    def save_as_dict(self):
        # To-Do:
        # Write saved data
        # Add kOBjs in Tables
        # Add labels, and data
        # Add header
        kObjs = []
        for row in self.rows:
            for cell in row.cells:
                if cell.knowledgeObject is not None:
                    kObjs.append(cell.knowledgeObject)
        knowledgeObjects = [_.knowObjID for _ in kObjs]
        labels = self.labels.save_as_dict()
        data = [_.save_as_dict() for _ in self.data]
        header = self.header.save_as_dict()
        units = self.units.save_as_dict()
        textual_representation = [_.save_as_dict() for _ in self.textual_representations]

        return {
            'header': header,
            'labels': labels,
            'units': units,
            'data': data,
            'knowledgeObject_references': knowledgeObjects,
            'textual_representation': textual_representation
        }

    def _get_count_of_words_per_line(self, lines):
        res = []
        for line in lines:
            freq = 0
            distribution = line.distribution
            for element, frequency in distribution:
                if element == 'WORD':
                    freq = frequency
            res.append(freq)
        return res

    def line_with_only_words(self):

        line = None
        lines = []
        try:
            if isinstance(self.data[0], Row):
                # Every Data Line (Row) should have one Label.
                # So we will check here every Column and get the Column with the most
                # Words
                lines = self.cols
            else:
                lines = self.rows
        except:
            print("ok")

        words_per_line = self._get_count_of_words_per_line(lines)
        max_words = max(words_per_line)
        if max_words != 0:
            max_idx = words_per_line.index(max_words)
            line = lines[max_idx]

        return line


class Row:

    def __init__(self, jsonDump):
        self.cells = [Cell(cellDump) for cellDump in jsonDump['cells']]
        self.textual_representation: str = ''
        self.type = jsonDump['type']

    def to_io(self) -> io.Row:
        return io.Row(**{
            'cells': [_.to_io() for _ in self.cells],
            'type': self.type
        })

    def set_category(self, type: str):
        self.category = type
        for cell in self.cells:
            cell.category = type

    def save_as_dict(self):
        cells: List[Dict] = [_.save_as_dict() for _ in self.cells]
        return {
            'cells': cells
        }


class Column:
    COUNTER = 1

    def __init__(self, jsonDump):
        self.id = Column.COUNTER
        self.cells = [Cell(cellDump) for cellDump in jsonDump['cells']]
        self.type = jsonDump['type']
        self.textual_representation: str = ''
        Column.COUNTER += 1

    def to_io(self) -> io.Column:
        return io.Column(**{
            'cells': [_.to_io() for _ in self.cells],
            'type': self.type
        })

    def set_category(self, type: str):
        self.category = type
        for cell in self.cells:
            cell.category = type

    def save_as_dict(self):
        cells: List[Dict] = [_.save_as_dict() for _ in self.cells]
        return {
            'cells': cells
        }


class Cell:

    def __init__(self, jsonDump):
        self.textInCell = jsonDump['text'].rstrip().lstrip() if jsonDump['text'] is not None else ''
        self.type: str = jsonDump['type']
        self.category: str = jsonDump['category']
        self.annotations: List[Annotation] = []
        self.knowledgeObject = []

    def to_io(self) -> io.Cell:
        annotations = set(self.annotations)
        return io.Cell(**{
            'text': self.textInCell,
            'annotation_ids': [_.annotationID for _ in annotations]
        })

    def add_unit(self, unit: str):
        self.textInCell += " " + unit

    def save_as_dict(self):
        text: str = self.textInCell
        category: str = self.category
        if self.knowledgeObject is not None:
            knowledgeObject: int = self.knowledgeObject.knowObjID
            return {
                'text': text,
                'knowledgeObject_references': [knowledgeObject],
                'category': category
            }

        return {
            'text': text,
            'category': category
        }
