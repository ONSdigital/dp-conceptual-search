from typing import List

from dp_conceptual_search.config import SEARCH_CONFIG

from dp_conceptual_search.search.search_type import SearchType
from dp_conceptual_search.ons.search.client.abstract_search_engine import AbstractSearchEngine

from dp_conceptual_search.ons.search import ContentType, AvailableTypeFilters, SortField
from dp_conceptual_search.ons.search.queries import type_counts_query
from dp_conceptual_search.ons.search.queries import content_query, function_score_content_query, departments_query


class SearchEngine(AbstractSearchEngine):
    """
    Implementation of the ONS search engine
    """
    default_page_number = 1
    agg_bucket = "docCounts"

    def departments_query(self, search_term: str, current_page: int, size: int):
        """
        Builds the ONS departments query with pagination
        :param search_term:
        :param current_page:
        :param size:
        :return:
        """
        s: SearchEngine = self._clone() \
            .query(departments_query(search_term)) \
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
        :param filter_functions:
        :param type_filters:
        :param kwargs:
        :return:
        """
        # Build the query dict
        query = content_query(search_term)

        # Add function scores if specified
        if filter_functions is not None:
            query = function_score_content_query(query, filter_functions)

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
        s: SearchEngine = self.content_query(search_term, self.default_page_number, SEARCH_CONFIG.results_per_page,
                                             type_filters=type_filters, highlight=False)

        # Build the aggregations
        aggregations = type_counts_query()

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
