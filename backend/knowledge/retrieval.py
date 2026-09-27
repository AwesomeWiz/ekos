from embeddings.bge_embeddings import BGEEmbeddingService
from graph.neo4j_service import Neo4jService
from vector_db.chroma_service import ChromaService


class KnowledgeRetrievalService:
    def __init__(
        self,
        neo4j: Neo4jService | None = None,
        chroma: ChromaService | None = None,
        embeddings: BGEEmbeddingService | None = None,
    ):
        self.neo4j = neo4j or Neo4jService()
        self.chroma = chroma or ChromaService()
        self.embeddings = embeddings or BGEEmbeddingService()

    def semantic_search(self, query: str, top_k: int = 5):
        embedding = self.embeddings.embed(query)

        results = self.chroma.search(
            embedding=embedding,
            top_k=top_k,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        return [
            {
                "id": ids[index],
                "text": documents[index],
                "metadata": metadatas[index],
                "distance": distances[index],
            }
            for index in range(len(documents))
        ]

    def graph_search(self, query: str, max_results: int = 10):
        search_term = query.strip()

        if not search_term:
            return []

        cypher = """
        MATCH (n)
        WHERE
            toLower(coalesce(n.name, '')) CONTAINS toLower($term)
            OR toLower(coalesce(n.title, '')) CONTAINS toLower($term)
            OR toLower(coalesce(n.message, '')) CONTAINS toLower($term)
            OR toLower(coalesce(n.login, '')) CONTAINS toLower($term)
            OR toLower(coalesce(n.full_name, '')) CONTAINS toLower($term)
            OR toLower(coalesce(n.id, '')) CONTAINS toLower($term)

        OPTIONAL MATCH path = (n)-[r*1..2]-(related)

        RETURN
            n.id AS id,
            labels(n) AS types,
            properties(n) AS properties,
            collect(
                DISTINCT {
                    node_id: related.id,
                    node_types: labels(related),
                    node_properties: properties(related),
                    relationships: [
                        rel IN relationships(path) |
                        {
                            type: type(rel),
                            properties: properties(rel)
                        }
                    ]
                }
            ) AS related_nodes

        LIMIT $max_results
        """

        with self.neo4j.driver.session() as session:
            result = session.run(
                cypher,
                term=search_term,
                max_results=max_results,
            )

            return [
                {
                    "id": record["id"],
                    "types": record["types"],
                    "properties": record["properties"],
                    "related_nodes": record["related_nodes"],
                }
                for record in result
            ]
        
    def retrieve_context(self, query: str, top_k: int = 5):
        vector_results = self.semantic_search(
            query=query,
            top_k=top_k,
        )

        graph_results = self.graph_search(query)

        if not graph_results:
            repositories = {
                result.get("metadata", {}).get("repository")
                for result in vector_results
                if result.get("metadata", {}).get("repository")
            }

            for repository in repositories:
                graph_results.extend(
                    self.graph_search(repository)
                )

        unique_graph_results = []
        seen_ids = set()

        for result in graph_results:
            result_id = result.get("id")

            if result_id in seen_ids:
                continue

            seen_ids.add(result_id)
            unique_graph_results.append(result)

        return {
            "query": query,
            "vector_results": vector_results,
            "graph_results": unique_graph_results,
        }

    def close(self):
        self.neo4j.close()