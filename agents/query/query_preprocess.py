from unidecode import unidecode


class QueryPreprocessor:
    def __init__(self, keep_alive: bool = True):
        self.keep_alive = keep_alive

    def encode(self, query: str) -> str:
        return unidecode(query)

    def trim_spaces(self, query: str) -> str:
        return " ".join(query.split())

    def make_lowercase(self, query: str) -> str:
        return query.lower()

    def preprocess(self, query: str) -> dict:
        encoded = self.encode(query)
        trimmed = self.trim_spaces(encoded)
        lowered = self.make_lowercase(trimmed)

        return {
            "original": query,
            "encoded": encoded,
            "trimmed": trimmed,
            "lowercase": lowered,
            "for_pcd": lowered,
            "length": len(lowered),
        }


query_preprocessor = QueryPreprocessor()
