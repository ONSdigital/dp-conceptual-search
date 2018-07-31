from elasticsearch_dsl import query as Q

from enum import Enum
from numpy import ndarray

from ons.search import fields
from core.word_embedding.models.supervised import SupervisedModel


class RescoreQuery(Q.Query):
    name = "rescore"


class ScriptScore(Q.Query):
    name = "script_score"


class FunctionScore(Q.Query):
    name = "function_score"


class Scripts(Enum):
    BINARY_VECTOR_SCORE = "binary_vector_score"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class ScriptLanguage(Enum):
    KNN = "knn"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class BoostMode(Enum):
    REPLACE = "replace"
    MULTIPLY = "multiply"
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


def vector_script_score(
        field: fields.Field,
        vector: ndarray,
        weight: float=1.0) -> Q.Query:
    params = {
        "cosine": True,
        "field": field.name,
        "vector": vector.tolist()
    }
    script_score = {
        "lang": ScriptLanguage.KNN.value,
        "params": params,
        "script": Scripts.BINARY_VECTOR_SCORE.value
    }

    if weight > 1:
        script_score['weight'] = weight

    # return script_score
    return ScriptScore(**script_score)


def date_decay_function() -> Q.Query:
    q = Q.SF('exp', **{fields.releaseDate.name: {
        "origin": "now",
        "scale": "365d",
        "offset": "30d",
        "decay": 0.5
    }})
    return q


def word_vector_keywords_query(
        search_term: str,
        model: SupervisedModel,
        k: int=10,
        threshold: float=0.1) -> Q.Query:
    """
    :param search_term:
    :param model:
    :param k:
    :param threshold:
    :return:
    """
    labels, probabilities = model.predict(
        search_term, k=k, threshold=threshold)

    match_queries = []
    for label, probability in zip(labels, probabilities):
        match_queries.append(Q.Match(
            **{fields.keywords.name: {"query": label.replace("_", " "), "boost": probability}}))

    query = Q.Bool(should=match_queries)
    return query


def user_rescore_query(
        user_vector: ndarray,
        score_mode: BoostMode=BoostMode.AVG,
        window_size: int=100,
        query_weight: float=0.5,
        rescore_query_weight: float=1.2) -> RescoreQuery:
    """
    Generates a rescore query from a users session vector
    :param user_vector:
    :param score_mode:
    :param window_size:
    :param query_weight:
    :param rescore_query_weight:
    :return:
    """
    user_script_score = vector_script_score(
        fields.embedding_vector, user_vector)

    rescore = {
        "window_size": window_size,
        "query": {
            "score_mode": score_mode.value,
            "rescore_query": {
                "function_score": user_script_score.to_dict()
            },
            "query_weight": query_weight,
            "rescore_query_weight": rescore_query_weight
        }
    }

    return RescoreQuery(**rescore)


def content_query(
        search_term: str,
        model: SupervisedModel,
        boost_mode: BoostMode=BoostMode.AVG,
        min_score: float=0.01,
        **kwargs) -> Q.Query:
    """
    Conceptual search (main) content query.
    Requires embedding_vectors to be indexed in Elasticsearch.
    :param search_term:
    :param model:
    :param boost_mode:
    :param min_score:
    :return:
    """
    from core.word_embedding.utils import clean_string

    from ons.search.filter_functions import content_filter_functions
    from ons.search.queries import content_query as ons_content_query

    search_vector = model.get_sentence_vector(clean_string(search_term))

    # Build the original ONS content query
    dis_max_query = ons_content_query(search_term)
    should = [dis_max_query]

    # Try to build additional keywords query
    try:
        tokens = [t.lower() for t in search_term.split()]
        known_tokens = [t for t in tokens if t in model.words]

        if len(known_tokens) > 0:
            known_search_terms = " ".join(known_tokens)
            terms_query = word_vector_keywords_query(
                known_search_terms, model)
            should.append(terms_query)
        else:
            from sanic.log import logger
            logger.debug(
                "No known words in query '%s' for keyword generation" %
                search_term)
    except ValueError as e:
        # Log the error but continue with the query (we can still return results, just can't
        # auto generate keywords for matching.
        # Note the script score will still facilitate non-keyword matching.
        from sanic.log import logger
        logger.warning(
            "Caught exception while generating model keywords: %s",
            str(e),
            exc_info=1)

    # Build function scores
    script_score = vector_script_score(fields.embedding_vector, search_vector)
    date_function = date_decay_function()

    function_scores = [script_score.to_dict(), date_function.to_dict()]

    # Add content type function scores if specified
    additional_function_scores = kwargs.get(
        "function_scores", content_filter_functions())

    if additional_function_scores is not None:
        if hasattr(additional_function_scores, "__iter__") is False:
            additional_function_scores = [additional_function_scores]
        function_scores.extend(additional_function_scores)

    # Build the final function score query
    function_score = FunctionScore(
        query=Q.Bool(should=should),
        min_score=min_score,
        boost_mode=boost_mode.value,
        functions=function_scores)

    return function_score


def recommended_content_query(
        page_uri: str,
        decoded_doc_vector: ndarray,
        user_vector: ndarray=None):
    """
    Query for recommended content using a page embedding vector and an (optional) user vector.
    :return:
    """
    from collections import OrderedDict

    from ons.search.queries import match_by_uri
    from ons.search.fields import embedding_vector

    from server.word_embedding.sanic_word2vec import Models, UnsupervisedModel
    from server.word_embedding.sanic_word2vec import load_model as load_unsup_model
    from server.word_embedding.sanic_supervised_models import SupervisedModels, SupervisedModel
    from server.word_embedding.sanic_supervised_models import load_model as load_sup_model

    # Build the function scores list
    doc_query = vector_script_score(embedding_vector, decoded_doc_vector)
    function_scores = [doc_query.to_dict()]

    # Finally, get similar terms to this vector for a terms query
    # Get a reference to the models
    unsupervised_model: UnsupervisedModel = load_unsup_model(Models.ONS)
    supervised_model: SupervisedModel = load_sup_model(SupervisedModels.ONS)

    similar_by_vector = [
        r[0] for r in unsupervised_model.model.similar_by_vector(decoded_doc_vector)]

    if user_vector is not None:
        # Build the user query
        user_query = vector_script_score(embedding_vector, user_vector)

        # Add to the function scores
        function_scores.append(user_query.to_dict())

        # Get similar words
        similar_by_vector.extend(
            [r[0] for r in unsupervised_model.model.similar_by_vector(user_vector)])

    # Remove duplicate terms from similar_by_vector and build sentence
    sentence = " ".join(list(OrderedDict.fromkeys(similar_by_vector)))

    # Build the keywords query from this sentence
    keywords_query = word_vector_keywords_query(sentence, supervised_model)

    # Explicitly exclude current page_uri
    query = Q.Bool(must_not=[match_by_uri(page_uri)], should=[keywords_query])

    # Build the function score query
    function_score_query = FunctionScore(
        query=query,
        functions=function_scores,
        boost_mode=BoostMode.AVG.value)

    return function_score_query
