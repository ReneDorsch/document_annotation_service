from app.core.config import MANUAL_NAMED_ENTITY_RECOGNITION, NAMED_ENTITY_RECOGNITION_MODEL_PATH
import snowballstemmer
import spacy
from flair.tokenization import SegtokTokenizer, SciSpacyTokenizer
from typing import List
import json
import torch
import flair


########################################################################################################################
# Some models to initiate

# Check if a gpu is available
# if it is the case use the gpu (default) else use cpu mode
if not torch.cuda.is_available():
    flair.device = torch.device('cpu')

POS_MODEL = spacy.load("en_core_sci_sm")
TOKENIZER = SciSpacyTokenizer()
STEMMER = snowballstemmer.stemmer('english')
with open(MANUAL_NAMED_ENTITY_RECOGNITION, "r") as file:
    MANUAL_NER_TAGS = json.load(file)

def load_table(path_to_table: str) -> List[str]:
    # Loads a dictionary (as a spellchecker) for checking data
    res = [_ for _ in json.load(open(path_to_table, 'r+'))['data']]
    return sorted(res, key=len, reverse=True)




