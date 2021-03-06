from typing import List

from dp_conceptual_search.search.query_helper import match_by_uri
from dp_conceptual_search.search.search_type import SearchType
from dp_conceptual_search.ons.search.client.abstract_search_engine import AbstractSearchEngine
from dp_conceptual_search.ons.search import SortField, AvailableTypeFilters, ContentType
from dp_conceptual_search.ons.search.queries.ons_query_builders import (
    build_content_query, build_type_counts_query, build_function_score_content_query, build_departments_query
)


class SearchEngine(AbstractSearchEngine):
    """
    Implementation of the ONS search engine
    """
    default_page_number = 1
    agg_bucket = "docCounts"

    def match_by_uri(self, uri: str):
        """
        Builds a simple match by uri query
        :param uri:
        :return:
        """
        query = match_by_uri(uri)
        return self.query(query)

    def departments_query(self, search_term: str, current_page: int, size: int):
        """
        Builds the ONS departments query with pagination
        :param search_term:
        :param current_page:
        :param size:
        :return:
        """
        s: SearchEngine = self._clone() \
            .query(build_departments_query(search_term)) \
            .paginate(current_page, size) \
            .search_type(SearchType.DFS_QUERY_THEN_FETCH)

        return s

    def content_query(self, search_term: str, current_page: int, size: int,
                      sort_by: SortField=SortField.relevance,
                      highlight: bool=True,
                      filter_functions: List[ContentType]=None,
                      type_filters: List[ContentType]=None,
                      **kwargs):
        """
        Builds the ONS content query, responsible for populating the SERP
        :param search_term:
        :param current_page:
        :param size:
        :param sort_by:
        :param highlight:
        :param filter_functions: content types to generate filter scores for (content type boosting)
        :param type_filters: content types to filter in query
        :param kwargs:
        :return:
        """
        # Build the query dict
        query = build_content_query(search_term)

        # Add function scores if specified
        if filter_functions is not None:
            query = build_function_score_content_query(query, filter_functions)

        # Build the content query
        s: SearchEngine = self._clone() \
            .query(query) \
            .paginate(current_page, size) \
            .sort_by(sort_by) \
            .search_type(SearchType.DFS_QUERY_THEN_FETCH)

        if type_filters is not None:
            s: SearchEngine = s.type_filter(type_filters)

        if highlight:
            s: SearchEngine = s.apply_highlight_fields()

        return s

    def type_counts_query(self, search_term, type_filters: List[ContentType]=None, **kwargs):
        """
        Builds the ONS type counts query, responsible providing counts by content type
        :param search_term:
        :param type_filters:
        :param kwargs:
        :return:
        """
        # Build the content query with no type filters, function scores or sorting
        s: SearchEngine = self.content_query(search_term,
                                             0,  # hard code page number to 0, as it does not impact the aggregations
                                             0,  # hard code page number to 0, as it does not impact the aggregations
                                             type_filters=type_filters, highlight=False)

        # Build the aggregations
        aggregations = build_type_counts_query()

        # Setup the aggregations bucket
        s.aggs.bucket(self.agg_bucket, aggregations)

        return s

    def featured_result_query(self, search_term):
        """
        Builds the ONS featured result query (content query with specific type filters)
        :param search_term:
        :return:
        """
        type_filters: List[ContentType] = AvailableTypeFilters.FEATURED.value.get_content_types()

        page_size = 1  # Only want one hit

        return self.content_query(search_term,
                                  self.default_page_number,
                                  page_size,
                                  filter_functions=None,
                                  type_filters=type_filters,
                                  highlight=False)
