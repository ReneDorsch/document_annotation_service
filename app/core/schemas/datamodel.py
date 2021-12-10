from __future__ import annotations

from typing import List, Union

from pydantic import BaseModel, Field



class Annotation(BaseModel):
    id: int
    words: List[Word]
    category: str

class KnowledgeObject(BaseModel):
    id: int
    category: str
    labels: List[str]
    annotation_ids: List[int]

class Word(BaseModel):
    id: int
    prev_word_id: int
    text: str
    normalized_text: str
    enriched_text: str
    annotation_id: int
    start_pos: int
    end_pos: int

class Text(BaseModel):
    chapters: List[Chapter] = Field(description='The actual textual information of the document.')
    abstract: Chapter = Field(default=None)


class Chapter(BaseModel):
    paragraphs: List[Paragraph] = Field(description="A list of paragraphs identified for this chapter. ")


class Paragraph(BaseModel):
    sentences: List[Sentence] = Field(description="A list of sentences identified for this chapter. ")



class Sentence(BaseModel):
    text: str = Field(default='', description="The text from this sentence")
    words: List[Word] = Field(default=[])


class Table(BaseModel):
    rows: List[Row] = Field(description="A list of rows for the table. ")
    columns: List[Column] = Field(description="A list of columns for the table. ")
    table_header: Union[Column, Row] = Field(default=None, description="A Line that corresponds to the header.")
    units: List[str] = Field(default=[], description="A Line that corresponds to the identified units in the table.")


class Line(BaseModel):
    cells: List[Cell] = Field(description="A list of cells at their position in the Line ")


class Row(Line):
    cells: List[Cell] = Field(description="A list of Cells in the row. ")
    type: str = Field(default='')


class Column(Line):
    cells: List[Cell] = Field(description="A list of Cells in the column. ")
    type: str = Field(default='')


class Cell(BaseModel):
    text: str
    category: str = Field(default='')
    type: str = Field(default='')
    annotation_ids: List[int] = Field(default=[])

class ResponseDocument(BaseModel):
    document_id: str = Field(description="An ID that helps to uniquely identify a document. ")
    text: Text = Field(description="The extracted textinformation of the document. ")
    tables: List[Table] = Field(description="A list of tables extracted from the document. ")
    annotations: List[Annotation] = []
    knowledgeObjects: List[KnowledgeObject] = []


class Metadata(BaseModel):
    abstract: Chapter = Field(default=None,
                              description='The Abstract of the document. ')

class Document(BaseModel):
    id: str
    text: Text
    metadata: Metadata
    tables: List[Table] = Field(description='The Tables of the document.', default=[])
    annotations: List = []
    knowledgeObjects: List = []

    def to_output_model(self) -> ResponseDocument:
        return ResponseDocument(**{
            'document_id': self.id,
            'text': self.text.to_io(),
            'tables': [_.to_io() for _ in self.tables],
            'annotations': [_.to_io() for _ in self.annotations],
            'knowledgeObjects': [_.to_io() for _ in self.knowledgeObjects]
        })





Sentence.update_forward_refs()
Chapter.update_forward_refs()
Paragraph.update_forward_refs()
Text.update_forward_refs()
Table.update_forward_refs()
Row.update_forward_refs()
Column.update_forward_refs()
Annotation.update_forward_refs()
ResponseDocument.update_forward_refs()