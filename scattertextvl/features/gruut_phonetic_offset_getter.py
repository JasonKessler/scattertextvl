from typing import List, Tuple, Union, Dict, Optional, Iterator

import gruut
from gruut_ipa import Phoneme


class PhoneticsGetterBase:
    def get_metadata(
            self,
            text: str
    ) -> List[Tuple[str, List[Union[int, List[Tuple[int, int]]]]]]:
        raise NotImplementedError()

    def get_definitions(self):
        return None


# copied from https://stackoverflow.com/a/30609050
def find_ngrams(input_list: List, n: int) -> Iterator:
    return zip(*[input_list[i:] for i in range(n)])


class GruutIPASymbolGetterBase(PhoneticsGetterBase):
    def __init__(self, lang: str = 'en-us', ngrams: Optional[List[int]] = None, **kwargs):
        self.lang = lang
        self.ngrams = [1] if ngrams is None else ngrams

    def get_metadata(
            self,
            text: str
    ) -> List[Tuple[str, List[Union[int, List[Tuple[int, int]]]]]]:
        offset_tokens = {}
        word_end = 0
        nlp = None
        for sent in gruut.sentences(text, lang=self.lang):
            for word in sent:

                # some tokens can be transcribed as multiple words by Gruut ($10 -> "ten dollars")
                # or (100 -> "one hundred")
                # for now, just ignore these and set their spans to 0,0
                # To do: fix this
                word_start, word_end = 0, 0
                if word.text.lower() in text.lower()[word_end:]:
                    word_start = text.lower().index(word.text.lower(), word_end)
                    word_end = word_start + len(word.text)

                if word.phonemes:
                    for ngram_size in self.ngrams:
                        phonemes = list(word.phonemes)
                        phoneme_ngrams = find_ngrams(
                            phonemes if ngram_size == 1
                            else ['_'] + phonemes + ['_'],
                            ngram_size
                        )
                        for ipa_sequence in phoneme_ngrams:
                            ngram = ''.join(ipa_sequence)
                            self._add_ipa_to_offset_tokens(
                                ngram,
                                offset_tokens,
                                word,
                                (word_start, word_end)
                            )
        return offset_tokens

    def _add_ipa_to_offset_tokens(
            self,
            ipa: str,
            offset_tokens: Dict[str, List[Union[int, List[Tuple[int, int]]]]],
            word,  # gruut.const.Word,
            word_start_end: Tuple[int, int]
    ):
        raise NotImplementedError()


class GruutIPASymbolGetter(GruutIPASymbolGetterBase):
    def _add_ipa_to_offset_tokens(
            self,
            ipa: str,
            offset_tokens: Dict[str, List[Union[int, List[Tuple[int, int]]]]],
            word,  #: gruut.const.Word,
            word_start_end: Tuple[int, int],
    ):
        offset_tokens.setdefault(ipa, [0, []])
        offset_tokens[ipa][0] += 1
        offset_tokens[ipa][1].append(word_start_end)


class GruutIPASymbolPropertyGetter(GruutIPASymbolGetterBase):
    def __init__(self, lang: str = 'en-us', ngrams: Optional[List[int]] = None, **kwargs):
        self.lang = lang
        kwargs.setdefault('ignore_properties', ['text', 'letters', 'type'])

    def _add_ipa_to_offset_tokens(
            self,
            ipa: str,
            offset_tokens: Dict[str, List[Union[int, List[Tuple[int, int]]]]],
            word,  #: gruut.const.Word,
            word_start_end: Tuple[int, int],
    ):
        for key, value in Phoneme(ipa).to_dict().items():
            if key not in ['text', 'letters']:
                ipa_properties = []
                if type(value) in [str, bool]:
                    if value != '':
                        ipa_properties.append(f'{key}-{value}')
                if type(value) == list:
                    for item in value:
                        ipa_properties.append(f'{item}-{value}')
                for ipa_property in ipa_properties:
                    offset_tokens.setdefault(ipa_property, [0, []])
                    offset_tokens[ipa_property][0] += 1
                    offset_tokens[ipa_property][1].append(word_start_end)


class PhoneticsFeatAndOffsetGetter(st.FeatAndOffsetGetter):
    def __init__(
            self,
            phonetics_getter: PhoneticsGetterBase,
    ):
        self.phonetics_getter = phonetics_getter

    def get_term_offsets(self, doc):
        return []

    def get_metadata_offsets(self, doc) -> List[Tuple[str, List[Union[int, List[Tuple[int, int]]]]]]:
        offset_tokens = self.phonetics_getter.get_metadata(str(doc))
        return list(offset_tokens.items())

    def get_definitions(self):
        return self.phonetics_getter.definitions()


