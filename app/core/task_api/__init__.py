import os

from pydantic import BaseModel, Field

from ..annotation_modul.apis import AnnotationStrategy, TextStrategy, TableStrategy, KnowledgeObjectStrategy
from ..annotation_modul.annotation_model import DocumentAnalysis

textAPI: TextStrategy = TextStrategy()
tableAPI: TableStrategy = TableStrategy()
annotationAPI: AnnotationStrategy = AnnotationStrategy()
knowledgeObjectAPI: KnowledgeObjectStrategy = KnowledgeObjectStrategy()


class TaskSettings(BaseModel):
    client: str = Field(description="The IP of the client. ")
    document_id: str = Field(description="A unique identifier to a document. ")
    status: str = 'working'
    data: DocumentAnalysis = Field(default=None)

    def as_extractedData(self) -> 'ExtractedData':
        """ Returns the extracted data as a ExtractedData-Object."""
        return {}

    @classmethod
    async def asy_create(cls, **data):
        """ Creates a new Task asynchronicity. """
        data.update({
            "document_id": data['document'].id,
            "data": {'document': data['document'].dict()}
        })
        self = cls(**data)
        return self

    @classmethod
    def create(cls, **data):
        """ Creates a new Task. """
        data.update({
            "document_id": data['document'].id,
            "data": {'document': data['document'].dict()}
        })
        self = cls(**data)
        return self

    def finish_task(self) -> None:
        """ Cleaning up. """
        # Delete input and output files.
        os.remove(self.path_to_input_file)
        os.remove(self.path_to_output_file)
        del self


class Task:
    """ A Class representing disitinct tasks as e.g. defined by execute_annotation.
    If you want to add additional Tasks describe the single functions of them in a staticmethod.

    This Task has to have a few concepts integrated:
    - It has to change the status to finished if the task is done.
    - And it has to save the transformed data in the TaskSettings.

    A Template for this would be:

    @staticmethod
    def do_some_task(task_settings: TaskSettings) -> None:
        # Do your stuff here
        ...
        task_settings.data = transforemd_data
        task_settings.status = 'finished'
    """

    @staticmethod
    def execute_annotation(task_settings: TaskSettings) -> None:
        """ Extracts Text, Tables, Images, and Metadata from the PDF. """
        data = task_settings.data.document

        tableAPI.preprocess_data(data)
        textAPI.preprocess_data(data)
        annotationAPI.preprocess_data(data)
        knowledgeObjectAPI.preprocess_data(data)

        tableAPI.process_data(data)
        textAPI.process_data(data)
        annotationAPI.process_data(data)
        knowledgeObjectAPI.process_data(data)

        tableAPI.postprocess_data(data)
        textAPI.postprocess_data(data)
        annotationAPI.postprocess_data(data)
        knowledgeObjectAPI.postprocess_data(data)

        task_settings.data = data
        task_settings.status = 'finished'


class TaskBuilder:
    """ A Builder Class to create Tasksettings. """
    # Add here additional Tasks
    tasks = {'annotate': Task.execute_annotation}

    def __init__(self):
        self.tasks = {}

    async def asy_create_task(self, task: str, **args) -> TaskSettings:
        """ Creates a new Task asynchronicity. """
        executable_task = TaskBuilder.tasks[task]
        task_settings: TaskSettings = await TaskSettings.asy_create(**args)
        self.tasks[task_settings.document_id] = {'task': executable_task}
        return task_settings

    def create_task(self, task, **args) -> TaskSettings:
        """ Creates a new Task. """
        task = TaskBuilder.tasks[task]
        task_settings = TaskSettings.create(**args)
        self.tasks[task_settings.document_id] = task
        return task_settings

    def perform_task(self, task_settings) -> None:
        """ Executes the task as defined in the TaskSettings. """
        executable = self.tasks[task_settings.document_id]
        executable(task_settings)

class TaskStatus(BaseModel):
    status: str = Field(description="The Status of the task. This can be either 'working' or 'finished'. "
                                    "If the status is 'working' the results of the task are not ready for the response."
                                    "If the status is 'finished' call the api /extraction/get_data/{document_id}.")
    document_id: str = Field(description="An id specified by the user to distinguish the extraction tasks. ")
