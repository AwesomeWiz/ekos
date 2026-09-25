import os

from neo4j import GraphDatabase


class Neo4jService:
    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "ekospassword")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
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

    def close(self) -> None:
        self.driver.close()