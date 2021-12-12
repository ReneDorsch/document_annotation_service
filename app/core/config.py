import os

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

ABBREVIATIONS = os.path.join(CURRENT_DIRECTORY,"files/abbreviations.json")
ANNOTATION_INPUT_PARAMETERS = os.path.join(CURRENT_DIRECTORY,"files/tagSpecificationForInputParameters.json")
MANUAL_NAMED_ENTITY_RECOGNITION = os.path.join(CURRENT_DIRECTORY,"files/ner_tags_static.json")
NAMED_ENTITY_RECOGNITION_MODEL_PATH = os.path.join(CURRENT_DIRECTORY,"files/annotation_model/spanBert/final-model.pt")
CATEGORICAL_LABELS = os.path.join(CURRENT_DIRECTORY,"files/categorical_labels.json")
UNITS = os.path.join(CURRENT_DIRECTORY,"files/units.json")

ANNOTATION_SCORE = 0.9

