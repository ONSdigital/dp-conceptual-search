from typing import List

from elasticsearch_dsl.response import Response
from elasticsearch_dsl.response import Hit, HitMeta

from dp_conceptual_search.ons.search.sort_fields import SortField
from dp_conceptual_search.ons.search.response import SearchResult, ContentQueryResult, TypeCountsQueryResult
from dp_conceptual_search.ons.search.paginator import Paginator


class DotDict(dict):
    description_field_name = "description"
    """
    Simple class which wraps a dictionary and supports dot notation for setting values
    """
    def __init__(self, *args, **kwargs):
        super(DotDict, self).__init__(*args, **kwargs)

    def set_description_element(self, field_name, original_value, new_value):
        """
        Sets a value in the page description
        :param field_name:
        :param original_value:
        :param new_value:
        :return:
        """
        # First, check if the value of this field is a list
        if isinstance(self[self.description_field_name][field_name], list):
            if original_value in self[self.description_field_name][field_name]:
                # Get the index of the element in the list and replace it
                idx = self[self.description_field_name][field_name].index(original_value)
                self[self.description_field_name][field_name][idx] = new_value
        else:
            # Just replace the existing value with the new one
            self[self.description_field_name][field_name] = new_value

    def set_value(self, field_name, original_value, new_value):
        """
        Sets a value using '.' notation
        :param field_name:
        :param original_value:
        :param new_value:
        :return:
        """
        if field_name in self:
            self[field_name] = new_value
        elif "." in field_name:
            parts = field_name.split(".")
            if parts[0] == self.description_field_name and len(parts) <= 2:
                description_field = parts[1]
                self.set_description_element(description_field, original_value, new_value)
        else:
            raise Exception("Unable to set field %s" % field_name)


class ONSResponse(Response):

    @staticmethod
    def highlight_hit(hit_dict: dict, highlight_dict: dict, open_tag: str, close_tag: str) -> dict:
        """
        Process all fragments in a given highlight dict
        :param hit_dict:
        :param highlight_dict:
        :param open_tag:
        :param close_tag:
        :return:
        """
        # Iterate over highlighted fields
        for highlight_field in highlight_dict:
            # Replace the _source field with the highlighted fragment, provided there is only one
            for highlighted_value in highlight_dict[highlight_field]:
                if isinstance(highlighted_value, str) and open_tag in highlighted_value \
                        and close_tag in highlighted_value:
                    # Get the original value
                    idx_start = highlighted_value.index(open_tag) + len(open_tag)
                    idx_end = highlighted_value.index(close_tag)
                    original_value = highlighted_value[idx_start:idx_end].strip()

                    # Overwrite the _source field
                    hit_dict.set_value(highlight_field, original_value, highlighted_value)

        return hit_dict

    def highlight_all(self, tag="strong") -> List[DotDict]:
        """
        Checks response for highlighter fragments and applies them to each hit
        :return:
        """
        highlighted_hits = []

        open_tag = "<{tag}>".format(tag=tag)
        close_tag = "</{tag}>".format(tag=tag)

        hit: Hit
        for hit in self.hits:
            hit_dict = DotDict(hit.to_dict())
            if hasattr(hit, "meta") and isinstance(hit.meta, HitMeta):
                hit_meta: HitMeta = hit.meta

                # Remap type field
                hit_dict["_type"] = hit_meta.to_dict().get("doc_type", None)

                # Check if highlighting results in the hit meta
                if hasattr(hit_meta, "highlight") and hasattr(hit_meta.highlight, "to_dict"):
                    highlight_dict = hit_meta.highlight.to_dict()

                    # Process all fragments and highlight the hit
                    self.highlight_hit(hit_dict, highlight_dict, open_tag, close_tag)

            # Add the hit to the list
            highlighted_hits.append(hit_dict)

        return highlighted_hits

    def hits_to_json(self) -> List[DotDict]:
        """
        Converts the search hits to a list of JSON, with highlighting applied
        :return:
        """
        return self.highlight_all()

    def to_type_counts_query_search_result(self) -> SearchResult:
        """
        Converts an Elasticsearch response into a TypeCountsQueryResult
        :param doc_counts:
        :return:
        """
        result: TypeCountsQueryResult = TypeCountsQueryResult(self.aggregations)
        return result

    def to_featured_result_query_search_result(self) -> SearchResult:
        """
        Wrapper for to_single_search_result to be explicit for featured results
        :return:
        """
        return self.to_single_search_result()

    def to_single_search_result(self) -> SearchResult:
        """
        Converts an Elasticsearch response into a ContentQueryResult
        :return:
        """
        return self.to_content_query_search_result(1, 1, SortField.relevance)

    def to_departments_query_search_result(self, page_number: int, page_size: int) -> SearchResult:
        """
        Converts an Elasticsearch response into a ContentQueryResult. Note, for a departments query the only
        possible sort option is by relevence.
        :param page_number:
        :param page_size:
        :param sort_by:
        :return:
        """
        return self.to_content_query_search_result(page_number, page_size, SortField.relevance)

    def to_content_query_search_result(self, page_number: int, page_size: int, sort_by: SortField) -> SearchResult:
        """
        Converts an Elasticsearch response into a ContentQueryResult
        :param page_number:
        :param page_size:
        :param sort_by:
        :return:
        """
        hits = self.hits_to_json()

        paginator = Paginator(
            self.hits.total,
            page_number,
            result_per_page=page_size)

        result: ContentQueryResult = ContentQueryResult(
            self.hits.total,
            self.took,
            hits,
            paginator,
            sort_by
        )

        return result
