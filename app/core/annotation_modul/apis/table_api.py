from ._base_api_ import TransformationStrategy
from ..annotation_model import DocumentAnalysis
from app.core.annotation_modul.datamodels.table_model import Table, Row, Column, Cell
from app.core.annotation_modul.datamodels.text_models import Sentence
import re
from typing import List, Tuple, Union


class TableStrategy(TransformationStrategy):
    """ An Agent performing all necessary tasks for the extraction and transformation of the table. """

    def __init__(self):
        super().__init__()

    def preprocess_data(self, data: DocumentAnalysis) -> None:
        res = []
        for table in data.tables:
            table = Table(table.dict())
            table_header = table.get_table_header()
            table.lines = self._get_table_lines(table, table_header)
            table.units = self._get_list_of_table_units([table_header] + table.lines)
            self.table_to_sentence(table)
            res.append(table)
        data.tables = res



    def postprocess_data(self, data: DocumentAnalysis) -> None:
        for table in data.tables:
            self.update_cell_annotations(table)

    def process_data(self, data: DocumentAnalysis) -> None:
        """ Processes the found tables. """
        # Get the relevant pages
        pass



    def _get_table_lines(self, table, table_header):
        """ Get all lines with data. """
        if isinstance(table_header, Row):
            lines = table.rows
        else:
            lines = table.cols
        return lines


    def update_cell_annotations(self, table) -> None:

        table_header = table.get_table_header()
        if isinstance(table_header, Row):
            lines_to_update = table.cols
        else:
            lines_to_update = table.rows

        for line in table.lines:
            for _line in lines_to_update:
                for cell in line.cells:
                    for _cell in _line.cells:
                        if cell.textInCell == _cell.textInCell:
                            _cell.annotations = cell.annotations
                            _cell.knowledgeObject = cell.knowledgeObject




    def table_to_sentence(self, table) -> None:
        '''
        Transforms the table in a list of simple sentences.

        :return: None
        '''
        table_header = table.get_table_header()
        lines = table.lines
        units = table.units

        number_of_elements_in_line: int = len(lines[0].cells)

        for i in range(number_of_elements_in_line):
            for column, name, unit in zip(lines, table_header.cells, units):
                text: str = f"The {name.textInCell} has a value of {column.cells[i].textInCell}{unit if unit else ''}."
                text = re.sub(" +", " ", text)
                sentence = Sentence.from_table(
                    sentence=text,
                    table=table)
                table.textual_representations.append(sentence)
                #line.textual_representation = sentence

        c = """
        for line in lines:
            for cell, name, unit in zip(line.cells, table_header.cells, units):
                text: str = f"The {name.textInCell} has a value of {cell.textInCell}{unit if unit else ''}."
                text = re.sub(" +", " ", text)
                sentence = Sentence.from_table(
                    sentence=text,
                    table=table)
                table.textual_representations.append(sentence)
                line.textual_representation = sentence
        """


    def _get_list_of_table_units(self, lines: List[Union[Row, Column]]) -> List[str]:
        '''
        This function will return a list, of the size of a row or col, with units found in the table.
        To do this, we have some assumptions:
        - In one line (=col or column) can a complete set of units found
        - Not every entry in the line has to be a unit
        - Not the complet cell of the line has to be a unit
        - We know how a unit should look like (aka. we have a predefined list of potential Units)

        So a table could look for example like this (But also rotated 90 degree):

        | COF     |   Material     |   Pressure (GPa)   |   relative Humidity (%)  |
        | 0.62    |   reference    |   1.47             |   20                     |
        | 0.25    |   MXene        |   1.47             |   20                     |
        | 0.35    |   reference    |   0.80             |   20                     |
        | 0.21    |   MXene        |   0.80             |   20                     |
        | 0.35    |   reference    |   1.47             |   80                     |
        | 0.25    |   MXene        |   1.47             |   80                     |
        | 0.30    |   reference    |   0.80             |   80                     |
        | 0.20    |   MXene        |   0.80             |   80                     |

        The first line contains different units.
        These Units will be identfied and in the following form extracted:
        ['', '', 'GPa', '%']

        :return: This function will return a list, of the size of a row or col, with units found in the table.
        '''

        # A Regex that identifies Brackets
        regex = '(\(|\{|\[|]|\}|\))'

        res = []
        for line in lines:
            units_in_line = []
            for cell in line.cells:
                text_in_cell: str = re.sub(regex, "", cell.textInCell)
                _unit = " "
                for unit in Table.UNITS:
                    if f" {unit} " in f" {text_in_cell} ":
                        _unit = unit
                        break

                units_in_line.append(_unit)
            if len(list(filter(lambda a: a != " ", units_in_line))) > len(res):
                res = units_in_line
        return res

    def _get_list_of_table_labels(self) -> List[str]:
        # Check labels row/col if it has units, if so delete them
        def replace_maximum(regex, text):
            # The longest possible Result of the regex will be deleted from the string
            strings = [text[:m.start()] + text[m.end():] for m in re.finditer(regex, text)]
            shortest_str = min(strings, key=len)
            return shortest_str

        res = []
        for label in self.labels.cells:
            # only if the label has at least one Space between two words check it.
            if len(label.textInCell.rstrip().lstrip().split(' ')) > 1:
                regex = "(in| )(\[|\(| ).*(\)|\]| )?"
                if re.search(regex, label.textInCell):
                    label = replace_maximum(regex, label.textInCell)
                    res.append(label)
            else:
                res.append(label.textInCell)
        return res

    def _get_list_of_table_names(self) -> List[str]:

        line_with_o_words = self.line_with_only_words()

        if line_with_o_words is None:
            data = self.data[0]
            number_of_placeholders = len(data.cells)
            names = ['Sample'] * number_of_placeholders
        else:
            # The assumption here is, to say that the first recognised line should be the line with the names
            # It is most often true, as the investigations of serveral papers showed
            names = [_.textInCell for _ in line_with_o_words.cells]
        return names


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



    def set_cols(self, rows):

        cols = []
        col_size = len(rows)
        cells_per_row = [row.cells for row in rows]
        for row_number in range(len(cells_per_row[0])):
            cells_per_col = []
            for col_number in range(col_size):
                cells_per_col.append(cells_per_row[col_number][row_number])
            cols.append(Column(cells_per_col))

        return cols

    def identify_labels(self):
        # If a row or a column consists mostly of predefined labels it is a label_row
        # And the row or column has to be the first one or the directly after the labels
        label = ''
        hits_per_col = self.hits_per_line(self.cols)
        hits_per_row = self.hits_per_line(self.rows)
        ratio_for_cols = self.ratio_for_line(hits_per_col, self.cols)
        ratio_for_rows = self.ratio_for_line(hits_per_row, self.rows)
        best_ratio_for_cols = max(ratio_for_cols)
        best_ratio_for_rows = max(ratio_for_rows)

        best_fit_for_col = self.cols[ratio_for_cols.index(best_ratio_for_cols)]
        best_fit_for_row = self.rows[ratio_for_rows.index(best_ratio_for_rows)]

        if best_ratio_for_rows > best_ratio_for_cols and best_ratio_for_rows > 0.5:
            best_fit_for_row.set_category('Label')
            label = best_fit_for_row
        elif best_ratio_for_cols > best_ratio_for_rows and best_ratio_for_cols > 0.5:
            best_fit_for_col.set_category('Label')
            label = best_fit_for_col

        # If nothing has been found
        # The row or column with the most words in it is the label row or column
        if label == '':
            categories_per_row = [row.distribution for row in self.rows]
            categories_per_col = [col.distribution for col in self.cols]
            row_pos, row_freq = self._get_line_with_most_words(categories_per_row)
            col_pos, col_freq = self._get_line_with_most_words(categories_per_col)
            if row_freq > col_freq:
                label = self.rows[row_pos]
                label.set_category('Label')
            else:
                label = self.cols[col_pos]
                label.set_category('Label')

        self.labels = label

    def _get_line_with_most_words(self, categories_per_line):
        freq = 0
        line_pos_with_most_words = -1
        for line_pos, line in enumerate(categories_per_line):
            for distribution in line:
                if distribution[0] == 'WORD':
                    if distribution[1] > freq:
                        line_pos_with_most_words = line_pos
                        freq = distribution[1]
        return line_pos_with_most_words, freq

    def ratio_for_line(self, hits_per_line, lines):
        ratio_for_line = []
        for hits in hits_per_line:
            # for num in range(len(lines)):
            ratio_for_line.append(hits.count(True) / len(hits))
        return ratio_for_line

    def hits_per_line(self, line):
        hits_per_line = []
        for row in line:
            hits_for_line = []
            for cell in row.cells:
                hit = False
                for label in Table.CATEGORICAL_LABELS:
                    if re.search(label.lower(), " " + cell.textInCell.lower() + " "):
                        hit = True
                        break
                hits_for_line.append(hit)
            hits_per_line.append(hits_for_line)
        return hits_per_line

    def identify_data_points(self):

        if isinstance(self.labels, Column):
            for col in self.cols:
                if col is not self.labels:
                    col.set_category('Data')
                    self.data.append(col)
        else:
            for row in self.rows:
                if row is not self.labels:
                    row.set_category('Data')
                    self.data.append(row)
