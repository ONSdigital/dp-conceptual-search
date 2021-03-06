"""
This file contains queries for conceptual search
"""
from typing import List
from elasticsearch_dsl import query as Q

from dp_conceptual_search.search.boost_mode import BoostMode
from dp_conceptual_search.search.dsl.script_score import ScriptScore
from dp_conceptual_search.ons.search.queries import ons_query_builders
from dp_conceptual_search.search.dsl.function_score import FunctionScore
from dp_conceptual_search.ons.search.fields import AvailableFields, Field
from dp_conceptual_search.search.dsl.vector_script_score import VectorScriptScore
from dp_conceptual_search.search.dsl.date_decay_function import date_decay_function


# Build a date decay function to promote recent releases
date_function = date_decay_function(AvailableFields.RELEASE_DATE.value.name,
                                    "exp", "365d", "30d", decay=0.95)


def word_vector_keywords_query(labels: List[str]) -> Q.Query:
    """
    Build a bool query to match against generated keyword labels
    :param labels:
    :return:
    """
    # Use the raw keywords field for matching
    field: Field = AvailableFields.KEYWORDS_RAW.value

    # Remove _ from labels
    labels = [label.replace("_", " ") for label in labels]

    # Build the individual match queries
    match_queries = [Q.MultiMatch(**{
        "query": label,
        "fields": [field.name,
                   AvailableFields.SEARCH_BOOST.value.name,
                   AvailableFields.TITLE.value.name,
                   AvailableFields.SUMMARY.value.name]
    }) for label in labels]

    return Q.Bool(should=match_queries)


def build_content_query(search_term: str, labels: List[str], search_vector_script: VectorScriptScore) -> Q.Query:
    """
    Defines the ONS conceptual search content query
    :param search_term:
    :param labels:
    :param search_vector_script:
    :return:
    """
    wv_keywords_query = word_vector_keywords_query(labels)

    # Build function scores
    script_score_dict = search_vector_script.to_dict()

    # Generate additional word vector keywords query
    additional_keywords_query = FunctionScore(
        query=wv_keywords_query,
        functions=[script_score_dict],
        boost_mode=BoostMode.REPLACE.value
    )

    # Build a script to boost original babbage query (pre-conceptual search)
    boost_script = ScriptScore(
        script="_score * boostFactor",
        params={
            "boostFactor": 100
        }
    )

    # Build the original content query
    dis_max_query = FunctionScore(
        query=ons_query_builders.build_content_query(search_term),
        functions=[boost_script.to_dict()],
        boost_mode=BoostMode.REPLACE.value
    )

    # Combine the original babbage query with the new keywords search vector in a single Distance Maximum (DisMax) query
    query = Q.Bool(
        should=[dis_max_query, additional_keywords_query]
    )

    # Finally, wrap in a function score to boost by release date
    return FunctionScore(
        query=query,
        functions=[date_function.to_dict()],
        boost_mode=BoostMode.MULTIPLY.value
    )
