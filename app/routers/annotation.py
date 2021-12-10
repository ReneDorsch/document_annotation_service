from fastapi import APIRouter, File, UploadFile, BackgroundTasks, Request, Form, HTTPException, Response
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_200_OK

from app.core.schemas.datamodel import Document, ResponseDocument
from app.core.task_api import TaskBuilder, TaskStatus

router = APIRouter()

# The APIs necessary for the tasks

taskBuilderAPI: TaskBuilder = TaskBuilder()
finished_tasks_database = dict()


def get_state(document_id: str):
    """ Gets the state of the document. If the document is ready for the response to the Requester the state finished
    will be called."""
    if document_id in finished_tasks_database:
        return 'finished'
    else:
        return 'working'


def get_results(document_id: str) -> ResponseDocument:
    """ Returns the results of the document as the outputmodel (document). """
    return finished_tasks_database[document_id].data.to_output_model()


def get_results_images(document_id: str) -> ResponseDocument:
    """ Returns the images of a result of the document as the outputmodel (document). """
    return finished_tasks_database[document_id].data.to_image_model()


def get_results_metadata(document_id: str) -> ResponseDocument:
    """ Returns the metadata of a result of the document as the outputmodel (document). """
    return finished_tasks_database[document_id].data.to_metadata_model()


def get_results_text(document_id: str) -> ResponseDocument:
    """ Returns the text of a result of the document as the outputmodel (document). """
    return finished_tasks_database[document_id].data.to_text_model()


def get_results_tables(document_id: str) -> ResponseDocument:
    """ Returns the tables of a result of the document as the outputmodel (document). """
    return finished_tasks_database[document_id].data.to_table_model()

@router.get('/annotation/get_logs/', response_model=ResponseDocument, status_code=HTTP_200_OK)
def get_task_extraction(document_id: str):
    """ An API to get the extraction of the task. """
    state: str = get_state(document_id)
    if state == 'finished':
        res: ResponseDocument = get_results(document_id)
        return res
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND,
                            detail="Document not ready or not found")

@router.get('/annotation/get_task_results/', response_model=ResponseDocument, status_code=HTTP_200_OK)
def get_task_extraction(document_id: str):
    """ An API to get the extraction of the task. """
    state: str = get_state(document_id)
    if state == 'finished':
        res: ResponseDocument = get_results(document_id)
        return res
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND,
                            detail="Document not ready or not found")


@router.get('/annotation/get_knowledgeObjects/', response_model=ResponseDocument, status_code=HTTP_200_OK)
def get_task_extraction(document_id: str):
    """ An API to get the extraction of the task. """
    state: str = get_state(document_id)
    if state == 'finished':
        res: ResponseDocument = get_results_images(document_id)
        return res
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND,
                            detail="Document not ready or not found")


@router.get('/annotation/get_annotations/', response_model=ResponseDocument, status_code=HTTP_200_OK)
def get_task_extraction(document_id: str):
    """ An API to get the extraction of the task. """
    state: str = get_state(document_id)
    if state == 'finished':
        res: ResponseDocument = get_results_metadata(document_id)
        return res
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND,
                            detail="Document not ready or not found")


@router.get('/annotation/has_results/')
def has_extraction(document_id: str, response: Response):
    """ An API to get the extraction of the task. """
    state = get_state(document_id)
    if state == 'finished':
        response.status_code = HTTP_201_CREATED
    else:
        response.status_code = HTTP_204_NO_CONTENT
    return {}


@router.post('/annotation/extract_annotations', response_model=TaskStatus, status_code=HTTP_201_CREATED)
def extract_annotations(request: Request,
                        background_tasks: BackgroundTasks,
                        document: Document
                        ):
    """ An API that extracts Information from a single PDF-Document. """

    _job = dict(
        status='pending',
        document_id=document.id
    )
    background_tasks.add_task(bg_annotate, request, document)
    return _job


def bg_annotate(request, document: Document):
    task = taskBuilderAPI.create_task(task='annotate',
                                    client=request.client.host,
                                    document=document)

    taskBuilderAPI.perform_task(task)
    finished_tasks_database.update({
        document.id: task
    })

async def asy_bg_annotate(request, document: Document):
    task = await taskBuilderAPI.asy_create_task(task='annotate',
                                                client=request.client.host,
                                                document=document)

    taskBuilderAPI.perform_task(task)
    finished_tasks_database.update({
        document.id: task
    })


def bg_transform_pdf_to_data(request, document_id, file):
    task = taskBuilderAPI.create_task(task='annotate',
                                      client=request.client.host,
                                      document_id=document_id,
                                      file=file)

    taskBuilderAPI.perform_task(task)
    finished_tasks_database.update({
        document_id: task
    })
