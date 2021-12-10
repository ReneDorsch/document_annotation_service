from ._base_api_ import TransformationStrategy
from flair.data import Sentence as fdSentence
from flair.models import SequenceTagger
from ..annotation_model import DocumentAnalysis
from .util_functions import MANUAL_NER_TAGS
import re
from ..datamodels.annotation_model import Annotation
from ..datamodels.text_models import Sentence, Word, Text
from typing import List, Tuple
from ..apis.util_functions import NAMED_ENTITY_RECOGNITION_MODEL_PATH, TOKENIZER


class AnnotationStrategy(TransformationStrategy):
    NAMED_ENTITY_RECOGNITION_MODEL = SequenceTagger.load(NAMED_ENTITY_RECOGNITION_MODEL_PATH)
    def preprocess_data(self, data: DocumentAnalysis) -> None:
        pass

    def postprocess_data(self, data: DocumentAnalysis) -> None:
        pass

    def process_data(self, data: DocumentAnalysis) -> None:
        self.annotate_text(data.text)
        self.annotate_tables(data.tables)

        data.annotations = self.get_annotations_from_data(data)

    def get_annotations_from_data(self, data: DocumentAnalysis):
        annotations = []
        for table in data.tables:
            for sentence in table.textual_representations:
                annotations.extend(sentence.annotations)

        chapters = [data.text.abstract] + data.text.chapters
        for chapter in chapters:
            for paragraph in chapter.paragraphs:
                for sentence in paragraph.sentences:
                    annotations.extend(sentence.annotations)

        return annotations


    def annotate_text(self, text: Text, batchOfSentences: bool = True, batchsize: int = 64) -> None:
        '''
        Annotates the data with Entities through the model given in the settings.py file

        :param batchOfSentences: True for annotating batches of Sentences instead of single sentences.
                                 It reduces the time needed for the task
        :return: None
        '''
        if batchsize < 1 and batchOfSentences and not isinstance(batchsize, int):
            print("Sorry you did something wrong. Check your batchsize (size > 0 and int) and if you want to use a "
                  "batch of sentences for the annotation task (True).")

        chapters = [text.abstract] + text.chapters
        sentences: List[Sentence] = []
        for chapter in chapters:
            for paragraph in chapter.paragraphs:
                sentences.extend(paragraph.sentences)

        self.annotate_sentences(sentences, batchOfSentences, batchsize)

    def annotate_tables(self, tables, batchOfSentences: bool = True, batchsize: int = 64) -> None:
        '''
        Annotates the data with Entities through the model given in the settings.py file

        :param batchOfSentences: True for annotating batches of Sentences instead of single sentences.
                                 It reduces the time needed for the task
        :return: None
        '''
        sentences: List[Sentence] = []
        for table in tables:
            sentences.extend(table.textual_representations)

        if batchsize < 1 and batchOfSentences and not isinstance(batchsize, int):
            print("Sorry you did something wrong. Check your batchsize (size > 0 and int) and if you want to use a "
                  "batch of sentences for the annotation task (True).")

        self.annotate_sentences(sentences, batchOfSentences, batchsize)

    def annotate_sentences(self, sentences: List[Sentence], state: bool, batchsize: int):
        '''

        :param state: Using single sentence annotation (False) or batch sentence annotations (True)
        :param batchsize: size of the Batch
        :return:
        '''


        self.annotate_with_model(batchsize, sentences, state)

        self.annotate_with_pattern_matching(sentences)

    def get_annotations(self, sentences: List[Sentence]) -> List[Annotation]:
        res = []
        for sentence in sentences:
            res.extend(sentence.annotations)
        return res

    def annotate_with_pattern_matching(self, sentences: List[Sentence]):
        # Use known names for annotations
        for sentence in sentences:
            self.set_manual_annotation(sentence)


        # Identify Acornyms
        found = 1
        while found != 0:
            annotations = self.get_annotations(sentences)

            found = 0
            # Identify Acronyms in the text
            for sentence in sentences:
                annotations = self.get_acronyms(sentence)
                sentence.annotations.extend(annotations)
                found += len(annotations)

            # Check if in any other sentence the acronym was used
            for annotation in annotations:
                for sentence in sentences:
                    found += self._pattern_matching(sentence, annotation)

    def _pattern_matching_for_textual_strings(self, sentence: Sentence, annotation: Annotation,
                                              inNormalizedForm: bool = True):
        found_matches = 0
        new_annos = []

        label = annotation.getWordsAsString(inNormalizedForm)

        try:
            is_small: bool = len(label) == 1
            is_lower: bool = label.islower()
            is_large: bool = len(label) > 3
            if is_large:

                for match in re.finditer(re.escape(label), sentence.getText(inNormalizedForm)):
                    words = sentence.get_words_of_span((match.start(), match.end()), useNormalizedForm=True)

                    if any([_.hasAnnotation for _ in words]): continue

                    label = " ".join([word.word for word in words])
                    try:
                        startPosition = min([_.startPos for _ in words])
                        endPosition = max([_.endPos for _ in words])
                    except:
                        print("ok")
                    # Adds a new Annotation
                    anno = Annotation.create_manual_annotation(label, startPosition, endPosition,
                                                               annotation.category,
                                                               annotation.specificCategory, words)
                    anno.addSynonym(annotation)
                    sentence.annotations.append(anno)
                    new_annos.append(anno)
                    found_matches += 1
                    anno.textualPatternMatch = True


            elif is_small and not is_lower:

                label = annotation.getWordsAsString(useNormalizedForm=False)

                regex = "( |^)" + re.escape(label) + "(?=(\.|,|\(|\[| |;))"

                for match in re.finditer(regex, sentence.textInSentence.lower()):
                    start = match.start()
                    end = match.end()
                    if match.group()[0] == " ":
                        start += 1
                    words = sentence.get_words_of_span((start, end), useNormalizedForm=False)
                    # Checks if the words are already part of an annotation
                    if any([_.hasAnnotation for _ in words]): continue

                    label = " ".join([word.word for word in words])
                    startPos = min([word.startPos for word in words])
                    endPos = max([word.endPos for word in words])
                    # Adds a new Annotation
                    anno = Annotation.create_manual_annotation(label, startPos, endPos, annotation.category,
                                                               annotation.specificCategory, words)
                    anno.addSynonym(annotation)
                    sentence.annotations.append(anno)
                    new_annos.append(anno)
                    found_matches += 1
                    anno.textualPatternMatch = True
        # if the word only consists of 1 char it is not a good idea to make manual annotations
        except re.error:
            print(label)

        return found_matches

    def annotate_with_model(self, batchsize, sentences, state):
        if state:
            self.batch_annotations(sentences, batchsize)
        else:
            self.single_annotations(sentences)

    def batch_annotations(self, sentences: List[Sentence], batch_size: int = 64):
        '''
        Creates Batches of Sentences that will be parallel analysed by the
        model.
        :param batch_size: Number of Sentences parallel analysed
        :return: by the Model annotated Sentences
        '''

        batch = []
        counter = 0

        for num, sentence in enumerate(sentences, 1):
            if num % batch_size == 0:
                AnnotationStrategy.NAMED_ENTITY_RECOGNITION_MODEL.predict(batch)
                for annotatedSentence in batch:
                    self.set_annotation_from_model(sentences[counter], annotatedSentence)
                    counter += 1
                batch = []

            batch.append(fdSentence(sentence.text_in_sentence, use_tokenizer=TOKENIZER))

        if len(batch) > 0:
            AnnotationStrategy.NAMED_ENTITY_RECOGNITION_MODEL.predict(batch)
            for annotatedSentence in batch:
                self.set_annotation_from_model(sentences[counter], annotatedSentence)
                counter += 1

    def single_annotations(self, sentences):
        for sentence in sentences:
            annotatedSentence = fdSentence(sentence.textInSentence, use_tokenizer=TOKENIZER)
            AnnotationStrategy.NAMED_ENTITY_RECOGNITION_MODEL.predict(annotatedSentence)
            self.set_annotation_from_model(sentence, annotatedSentence)


    def set_annotation_from_model(self, sentence: Sentence, flair_sentence: fdSentence) -> None:
        def delete_paranthesis(span, wordList: List[Word]):
            "/(){}[]\\"
            special_chars = ["(", ")", "{", "}", "[", "]", "\\"]
            first_word = wordList[0]
            last_word = wordList[-1]

            if first_word.word in special_chars:
                wordList.remove(first_word)
            if last_word.word in special_chars:
                wordList.remove(last_word)

            return span, wordList

        def delete_figures_and_tables(span, wordList: List[Word]):
            for word in wordList:
                if word.word.lower() in ["tab.", "tab", "table", "fig", "fig.", "figure"]:
                    return [], []
            return span, wordList

        for span in flair_sentence.get_spans('ner'):
            locationSpan: Tuple[int, int] = (min([x.start_pos for x in span.tokens]),
                                             max([x.end_pos for x in span.tokens]))
            wordList = sentence.get_words_of_span(locationSpan)
            span, wordList = delete_paranthesis(span, wordList)
            span, wordList = delete_figures_and_tables(span, wordList)

            if len(wordList) == 0:
                continue

            anno = Annotation.create_model_annotation(span, wordList)
            sentence.annotations.append(anno)

    def set_manual_annotation(self, sentence: Sentence) -> None:
        for tag, attribute in MANUAL_NER_TAGS.items():
            for synonym in attribute["tags"]:
                for match in re.finditer(re.escape(synonym.lower()), sentence.text_in_sentence.lower()):
                    try:
                        words = sentence.get_words_of_span(match.span())
                        # Checks if the words are already part of an annotation
                        if any([_.has_annotation for _ in words]): break

                        label = " ".join([word.word for word in words])
                        startPos = min([word.start_pos for word in words])
                        endPos = max([word.end_pos for word in words])

                        # Adds a new Annotation
                        anno = Annotation.create_manual_annotation(label, startPos, endPos,
                                                                   attribute["category"],
                                                                   attribute["specific_category"], words)
                        sentence.annotations.append(anno)
                    except:
                        words = sentence.get_words_of_span(match.span())

    def get_acronyms(self, sentence: Sentence) -> List[Annotation]:
        '''
        Identifies Acronyms and creates a new annotation for them.
        In addition it will add the Acronym to the annotation that are connected to them
        :return: Nothing
        '''
        # The Regex looks for Acronyms in Brackets
        # e.g. Deutschland (DE)
        res = []
        pattern = "(?<=\()\w+(?=(\)| |\.|,|;|:))"  # Find any smallest string that has at the beginning a ( and at the end a )
        for match in re.finditer(pattern, sentence.text_in_sentence):
            words: List[Word] = sentence.get_words_of_span(match.span())
            # Checks if the words are already part of an annotation+

            first_word_in_tag = words[0]
            prevWord = first_word_in_tag.previous_word
            if prevWord.previous_word is not None:
                if prevWord.previous_word.has_annotation:
                    try:
                        prevAnnotation = prevWord.previous_word.annotation
                        already_annotated: bool = any([_.has_annotation for _ in words])
                        is_figure: bool = any([_.word.lower() in ['figure', 'fig', 'fig.'] for _ in words])
                        is_table: bool = any([_.word.lower() in ['table', 'tab', 'tab.'] for _ in words])

                        if not already_annotated and not (is_figure or is_table):

                            ### if the Acronym is in () -> as it should be
                            ### check wether it is in the span found by the regex
                            ### and if it is taken as a seperate word
                            ### dont annotate it as a acronym
                            # words = [word for word in words if word.word != '(' or word.word != ')']

                            words = [word for word in words if word.word.rstrip().lstrip()]
                            label = " ".join([word.word for word in words])
                            startPos = min([word.start_pos for word in words])
                            endPos = max([word.end_pos for word in words])

                            category = prevAnnotation.category
                            specificCategory = prevAnnotation.specificCategory

                            # Adds a new Annotation

                            anno = Annotation.create_manual_annotation(label, startPos, endPos, category,
                                                                       specificCategory, words)
                            res.append(anno)
                        elif already_annotated:
                            anno = [_ for _ in words if _.has_annotation][0].annotation

                        if not (is_figure or is_table):
                            anno.addSynonym(prevAnnotation)
                            sentence.annotations.append(anno)
                    except:
                        print("error")
                        words = sentence.get_words_of_span(match.span())
        return res

    def _pattern_matching(self, sentence, annotation: Annotation, inNormalizedForm: bool = True):
        '''
        Annotates words that are not already annotated by there representation in the text
        :param annotation:
        :param inNormalizedForm:
        :return:
        '''

        label = annotation.getWordsAsString(inNormalizedForm)
        # First check if the annotation contains a number
        # If so do another routine
        # Delete , .

        potential_number_label = re.sub("(\.|,)", "", label)
        if any([_.isdigit() for _ in potential_number_label.split(' ')]):
            return self._pattern_matching_for_numerical_strings(sentence, annotation)

        else:
            return self._pattern_matching_for_textual_strings(sentence, annotation, inNormalizedForm)

        return found_matches

    def _pattern_matching_for_numerical_strings(self, sentence: Sentence, annotation: Annotation):
        '''

        :param annotation:
        :return:
        '''

        #########################################################################################
        # A numerical values as a string is distinctable from a normal string.
        # It has the possibilitiy to say with different representations the same thing
        # E.g
        # 0.80 GPa == 0.8 GPa         <-- first example
        # 0.80 GPa == 800 MPa         <-- second example
        # 0.80 GPa == 0,80 GPa        <-- third example
        # 0.80 GPa == 0.80 gpa        <-- fourth example
        # 0.80 GPa == 0.80 gigapascal <-- fifth example
        # While the first example shows that the semantic of the single numerical value is equal
        # the second example shows a different semantics. The Semantics of the unit
        # Here i will consider all but the second kind of problem, because it is general. Whereas the second kind
        # should be considered in some kind of ontology or another type of knowledgerepresentation
        #########################################################################################

        found_matches = 0
        new_annos = []

        label = annotation.getWordsAsString(useNormalizedForm=True)

        to_small: bool = len(label) < 3
        if to_small:
            return found_matches

        # For the sentence we have to do the same
        new_annos = []

        regex = "( |^)" + re.escape(label) + "(?=(\.|, | \( | \[|))"

        for match in re.finditer(regex, sentence.getText(useNormalizedForm=True)):
            start = match.start()
            end = match.end()
            if match.group()[0] == " ":
                start += 1
            words = sentence.get_words_of_span((start, end), useNormalizedForm=True)
            # Checks if the words are already part of an annotation
            already_annotated: bool = any([_.has_annotation for _ in words])
            is_figure: bool = any([_.word.lower() in ['figure', 'fig', 'fig.'] for _ in words])
            is_table: bool = any([_.word.lower() in ['table', 'tab', 'tab.'] for _ in words])

            if not already_annotated and not (is_figure or is_table):
                label = " ".join([word.word for word in words])
                startPos = min([word.start_pos for word in words])
                endPos = max([word.end_pos for word in words])
                # Adds a new Annotation
                anno = Annotation.create_manual_annotation(label, startPos, endPos, annotation.category,
                                                           annotation.specificCategory, words)
                anno.addSynonym(annotation)
                sentence.annotations.append(anno)
                new_annos.append(anno)
                found_matches += 1
                anno.numericMatch = True

        return found_matches
