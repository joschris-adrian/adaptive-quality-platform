import os
from opensearchpy import OpenSearch

_client = None

def get_client() -> OpenSearch:
    global _client
    if _client is None:
        host = os.getenv("OPENSEARCH_HOST", "localhost")
        port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        _client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            use_ssl=False,
            verify_certs=False,
        )
    return _client