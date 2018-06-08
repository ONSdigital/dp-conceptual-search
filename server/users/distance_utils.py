import numpy as np


def default_distance_measure(
        original_vector: np.ndarray,
        term_vector: np.ndarray) -> np.ndarray:
    """
    Default method to measure distance between two vectors. Uses Euclidean distance.
    :param original_vector:
    :param term_vector:
    :return:
    """
    dist = term_vector - original_vector
    return dist


def default_move_session_vector(
        original_vector: np.ndarray,
        term_vector: np.ndarray) -> np.ndarray:
    """
    Default method to modify a session vector to reflect interest in a term vector.
    :param original_vector: Word vector representing the present session.
    :param term_vector: Word vector representing the term of interest.
    :return: An updated word vector which has moved towards the term vector in the full N-dimensional
    vector space.
    """
    import os

    lr = max(os.environ.get("SEARCH_LEARNING_RATE", 0.25), 1.0)
    dist = default_distance_measure(original_vector, term_vector)

    return original_vector + (dist * lr)
