import asyncio
from unittest import TestCase

from unit.elasticsearch.elasticsearch_test_utils import mock_search_client

from dp_conceptual_search.config import CONFIG

from dp_conceptual_search.search.client.search_client import SearchClient
from dp_conceptual_search.search.client.exceptions import RequestSizeExceededException


class SearchClientTestCase(TestCase):

    def setUp(self):
        super(SearchClientTestCase, self).setUp()

        self.mock_client = mock_search_client()

    @property
    def get_body(self):
        """
        Test query body
        :return:
        """
        body = {
            "query": {
                "match": {
                    "name": "Randy Marsh"
                }
            }
        }
        return body

    @property
    def index(self):
        """
        Returns the test index
        :return:
        """
        return "test"

    def get_client(self) -> SearchClient:
        """
        Create an instance of a SearchClient for testing
        :return:
        """

        client = SearchClient(using=self.mock_client, index=self.index)
        return client

    def test_search_called(self):
        """
        Tests that search was called with correct arguments
        :return:
        """
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

        async def run_async():
            client: SearchClient = self.get_client()

            # Call search and check arguments match those provided
            client.update_from_dict(self.get_body)

            response = await client.execute(ignore_cache=True)

            self.mock_client.search.assert_called_with(index=[self.index], doc_type=[], body=self.get_body)

        # Run the async test
        coro = asyncio.coroutine(run_async)
        event_loop.run_until_complete(coro())
        event_loop.close()

    def test_max_size_error(self):
        """
        Tests that a RequestSizeExceededException is raised when the request size is higher than
        CONFIG.SEARCH.max_request_size
        :return:
        """
        client: SearchClient = self.get_client()
        page_size = CONFIG.SEARCH.max_request_size + 1

        with self.assertRaises(RequestSizeExceededException) as context:
            client = client[0:page_size]

        self.assertTrue("Max request size exceeded" in str(context.exception))

