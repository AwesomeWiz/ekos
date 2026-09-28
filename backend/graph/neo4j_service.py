from neo4j import GraphDatabase, Query
from config.settings import settings


class Neo4jService:
    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        connection_timeout: float | None = None,
    ):
        self.uri = settings.NEO4J_URI if uri is None else uri
        self.username = settings.NEO4J_USERNAME if username is None else username
        self.password = settings.NEO4J_PASSWORD if password is None else password

        options = {} if connection_timeout is None else {
            "connection_timeout": connection_timeout,
            "connection_acquisition_timeout": max(5.0, connection_timeout * 2),
        }
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
            **options,
        )

    def verify_connection(self) -> bool:
        self.driver.verify_connectivity()
        return True

    def create_user(self, user_id: str, name: str, email: str | None = None) -> None:
        query = """
        MERGE (u:User {id: $user_id})
        SET u.name = $name,
            u.email = $email
        """

        with self.driver.session() as session:
            session.run(
                query,
                user_id=user_id,
                name=name,
                email=email,
            )

    def create_repository(
        self,
        repository_id: str,
        name: str,
        url: str | None = None,
    ) -> None:
        query = """
        MERGE (r:Repository {id: $repository_id})
        SET r.name = $name,
            r.url = $url
        """

        with self.driver.session() as session:
            session.run(
                query,
                repository_id=repository_id,
                name=name,
                url=url,
            )

    def create_commit(
        self,
        commit_id: str,
        message: str,
        author_id: str,
        repository_id: str,
    ) -> None:
        query = """
        MERGE (c:Commit {id: $commit_id})
        SET c.message = $message

        WITH c

        MATCH (u:User {id: $author_id})
        MATCH (r:Repository {id: $repository_id})

        MERGE (u)-[:COMMITTED]->(c)
        MERGE (c)-[:BELONGS_TO]->(r)
        """

        with self.driver.session() as session:
            session.run(
                query,
                commit_id=commit_id,
                message=message,
                author_id=author_id,
                repository_id=repository_id,
            )

    def create_issue(
        self,
        issue_id: str,
        title: str,
        repository_id: str,
        state: str | None = None,
    ) -> None:
        query = """
        MERGE (i:Issue {id: $issue_id})
        SET i.title = $title,
            i.state = $state

        WITH i

        MATCH (r:Repository {id: $repository_id})

        MERGE (i)-[:BELONGS_TO]->(r)
        """

        with self.driver.session() as session:
            session.run(
                query,
                issue_id=issue_id,
                title=title,
                repository_id=repository_id,
                state=state,
            )

    def create_pull_request(
        self,
        pull_request_id: str,
        title: str,
        repository_id: str,
        state: str | None = None,
    ) -> None:
        query = """
        MERGE (p:PullRequest {id: $pull_request_id})
        SET p.title = $title,
            p.state = $state

        WITH p

        MATCH (r:Repository {id: $repository_id})

        MERGE (p)-[:BELONGS_TO]->(r)
        """

        with self.driver.session() as session:
            session.run(
                query,
                pull_request_id=pull_request_id,
                title=title,
                repository_id=repository_id,
                state=state,
            )

    def create_document(
        self,
        document_id: str,
        title: str,
        content: str,
    ) -> None:
        query = """
        MERGE (d:Document {id: $document_id})
        SET d.title = $title,
            d.content = $content
        """

        with self.driver.session() as session:
            session.run(
                query,
                document_id=document_id,
                title=title,
                content=content,
            )

    def get_knowledge_relationships(self, entity_ids: list[str], limit: int = 6) -> list[dict]:
        """Read only neighbors of tenant-scoped entities from permitted search results."""
        query = """
        MATCH (source)-[r]->(target)
        WHERE (source.id IN $ids OR target.id IN $ids)
          AND source.organization_id = target.organization_id
          AND source.connector_id = target.connector_id
        RETURN DISTINCT coalesce(source.title, source.name, source.id) AS source,
               type(r) AS relationship, coalesce(target.title, target.name, target.id) AS target
        LIMIT $limit
        """
        with self.driver.session(default_access_mode="READ") as session:
            return [dict(record) for record in session.run(Query(query, timeout=5),
                    ids=entity_ids[:3], limit=max(1, min(limit, 6)))]

    def get_github_contributors(self, repository_ids: list[str], limit: int = 6) -> list[dict]:
        """One representative commit per contributor in the permitted repositories."""
        if not repository_ids:
            return []
        query = """
        MATCH (u:User)-[:COMMITTED]->(c:Commit)-[:BELONGS_TO]->(r:Repository)
        WHERE r.id IN $repository_ids OR r.url IN $repository_urls
        WITH coalesce(u.name, u.id) AS contributor, min(c.id) AS commit
        RETURN contributor AS source, 'COMMITTED' AS relationship, commit AS target
        ORDER BY source
        LIMIT $limit
        """
        with self.driver.session(default_access_mode="READ") as session:
            return [record.data() for record in session.run(Query(query, timeout=5),
                repository_ids=repository_ids[:3],
                repository_urls=[f"https://github.com/{repo}" for repo in repository_ids[:3]],
                limit=max(1, min(limit, 6)))]

    def get_github_relationships(self, repository_ids: list[str], terms: list[str], limit: int = 6) -> list[dict]:
        """Read the existing GitHub commit paths, restricted to permitted repositories."""
        if not repository_ids:
            return []
        limit = max(1, min(limit, 10))
        query = """
        MATCH (c:Commit)-[:BELONGS_TO]->(r:Repository)
        WHERE r.id IN $repository_ids OR r.url IN $repository_urls
        OPTIONAL MATCH (u:User)-[:COMMITTED]->(c)
        WITH r, c, u,
             CASE WHEN any(term IN $terms WHERE
                 toLower(coalesce(u.name, u.id, '')) CONTAINS term OR
                 toLower(coalesce(c.message, '')) CONTAINS term OR
                 toLower(coalesce(c.id, '')) CONTAINS term)
             THEN 1 ELSE 0 END AS relevance
        ORDER BY relevance DESC, c.id, u.id
        LIMIT $commit_limit
        UNWIND CASE WHEN u IS NULL THEN
            [{source: c.id, relationship: 'BELONGS_TO', target: coalesce(r.name, r.id)}]
        ELSE
            [{source: coalesce(u.name, u.id), relationship: 'COMMITTED', target: c.id},
             {source: c.id, relationship: 'BELONGS_TO', target: coalesce(r.name, r.id)}]
        END AS edge
        RETURN DISTINCT edge.source AS source, edge.relationship AS relationship, edge.target AS target
        LIMIT $limit
        """
        with self.driver.session(default_access_mode="READ") as session:
            records = session.run(
                Query(query, timeout=5.0), repository_ids=repository_ids,
                repository_urls=[f"https://github.com/{repo}" for repo in repository_ids],
                terms=terms, commit_limit=(limit + 1) // 2, limit=limit,
            )
            return [record.data() for record in records]

    def get_github_graph(self, repository_ids: list[str], limit: int = 6) -> dict:
        """Read a small subgraph from existing GitHub commit paths."""
        if not repository_ids:
            return {"nodes": [], "edges": []}
        query = """
        MATCH (c:Commit)-[:BELONGS_TO]->(r:Repository)
        WHERE r.id IN $repository_ids OR r.url IN $repository_urls
        OPTIONAL MATCH (u:User)-[:COMMITTED]->(c)
        RETURN r.id AS repository_id, r.name AS repository_name,
               c.id AS commit_id, c.message AS message,
               u.id AS user_id, coalesce(u.name, u.id) AS user_name
        ORDER BY r.id, c.id, u.id
        LIMIT $limit
        """
        nodes, edges = {}, {}
        with self.driver.session(default_access_mode="READ") as session:
            records = session.run(Query(query, timeout=5.0), repository_ids=repository_ids,
                                  repository_urls=[f"https://github.com/{repo}" for repo in repository_ids],
                                  limit=max(1, min(limit, 6)))
            for record in records:
                repo_id = f"Repository:{record['repository_id']}"
                commit_id = f"Commit:{record['commit_id']}"
                nodes[repo_id] = {"id": repo_id, "label": record["repository_name"] or record["repository_id"],
                                  "type": "Repository", "description": record["repository_id"]}
                nodes[commit_id] = {"id": commit_id, "label": str(record["commit_id"])[:12],
                                    "type": "Commit", "description": record["message"] or ""}
                edges[(commit_id, repo_id)] = {"source": commit_id, "target": repo_id, "relationship": "BELONGS_TO"}
                if record["user_id"] is not None:
                    user_id = f"User:{record['user_id']}"
                    nodes[user_id] = {"id": user_id, "label": record["user_name"], "type": "User", "description": ""}
                    edges[(user_id, commit_id)] = {"source": user_id, "target": commit_id, "relationship": "COMMITTED"}
        return {"nodes": list(nodes.values()), "edges": list(edges.values())}

    def close(self) -> None:
        self.driver.close()
