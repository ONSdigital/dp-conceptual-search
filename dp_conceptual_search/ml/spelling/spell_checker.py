"""
Implementation of a spellchecker using word embedding models
"""
from typing import Generator, List
from sortedcontainers import SortedSet

from dp_conceptual_search.ml.word_embedding.fastText.unsupervised import UnsupervisedModel

# Constant
LETTERS = 'abcdefghijklmnopqrstuvwxyz'


class SpellCheckSuggestion(object):
    """
    Useful class for defining a single suggested spelling correction
    """
    def __init__(self, input_token, correction, probability):
        self.input_token = input_token
        self.correction = correction
        self.probability = probability

    def to_dict(self) -> dict:
        return {
            "input": self.input_token,
            "correction": self.correction,
            "probability": self.probability
        }


class SpellChecker(object):
    """
    Uses word embedding models to check the spelling of words and suggested corrections.
    """

    def __init__(self, model: UnsupervisedModel):
        self.model: UnsupervisedModel = model

    @property
    def words(self) -> dict:
        return self.model.words

    def correct_spelling(self, terms: List[str]) -> List[SpellCheckSuggestion]:
        """
        Returns a list of potential (best candidate) corrections, with their probabilities.
        :param terms:
        :return:
        """
        result = []

        for term in SortedSet(terms):
            correction = self.correction(term)
            if correction.lower() != term.lower():
                probability = self.probability(correction)
                if probability != 0:
                    result.append(SpellCheckSuggestion(term, correction, probability))
        return result

    def probability(self, word) -> float:
        """
        Probability of `word` being the correct substitution.
        Returns 0 if the word isn't in the dictionary
        """
        if word not in self.words:
            return 0.
        num_words = float(len(self.words))
        word_idx = float(self.words.get(word, 0))
        return num_words / (word_idx + num_words)

    def correction(self, word) -> str:
        """ Most probable spelling correction for word. """
        return max(self.candidates(word), key=self.probability)

    def candidates(self, word) -> set:
        """ Generate possible spelling corrections for word. """
        return self.known(
            [word]) or self.known(
            self.single_edit_candidates(word)) or self.known(
            self.double_edit_candidates(word)) or [word]

    def known(self, words) -> set:
        """ The subset of `words` that appear in the dictionary. """
        return set(w for w in words if w in self.words)

    def single_edit_candidates(self, word) -> set:
        """ All candidate words that are one edit away from `word`. """
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        # All words one deletion away from word
        deletes = [left + right[1:] for left, right in splits if right]
        # All words one transposition away from word
        transposes = [left + right[1] + right[0] + right[2:] for left, right in splits if len(right) > 1]
        # All words with one character replacement from word
        replaces = [left + char + right[1:] for left, right in splits if right for char in LETTERS]
        # All words one character insert away from word
        inserts = [left + char + right for left, right in splits for char in LETTERS]
        # Return set of all of the above
        return set(deletes + transposes + replaces + inserts)

    def double_edit_candidates(self, word) -> Generator:
        """ All candidate words that are two edits away from `word`. """
        return (e2 for e1 in self.single_edit_candidates(word) for e2 in self.single_edit_candidates(e1))
