"""Opt-in live demo check. Uses configured GitHub; never inserts fixture documents."""

import argparse
import os

import httpx


def login(client, email, password):
    response = client.post("/api/login", json={"email": email, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--query", default="repository branches")
    parser.add_argument("--repeat-sync", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=600.0) as client:
        admin = login(client, os.getenv("EKOS_ADMIN_EMAIL", "admin@aekos.com"), os.getenv("EKOS_ADMIN_PASSWORD", "admin123"))
        listing = client.get("/api/connectors", headers=admin)
        listing.raise_for_status()
        github = next(item for item in listing.json() if item["type"].lower() == "github")
        tested = client.post(f"/api/connectors/{github['id']}/test", headers=admin)
        tested.raise_for_status()
        print("GitHub connection:", tested.json()["status"], flush=True)
        totals = []
        for _ in range(2 if args.repeat_sync else 1):
            synced = client.post(f"/api/connectors/{github['id']}/sync", headers=admin)
            synced.raise_for_status()
            result = synced.json()
            print("GitHub sync:", result, flush=True)
            if result["indexing"]["status"] != "indexed":
                raise RuntimeError(result["indexing"]["error"])
            totals.append(result["indexing"]["chroma_total"])
        if args.repeat_sync and totals[0] != totals[1]:
            raise RuntimeError("Index totals changed on repeat sync; check whether the remote repository changed")
        developer = login(client, os.getenv("EKOS_TEST_EMAIL", "arnold@aekos.com"), os.getenv("EKOS_TEST_PASSWORD", "password123"))
        assert client.post(f"/api/connectors/{github['id']}/sync", headers=developer).status_code == 403
        status = client.get("/api/search/status", headers=developer)
        status.raise_for_status()
        print("Developer index status:", status.json(), flush=True)
        searched = client.post("/api/search", headers=developer, json={"query": args.query, "top_k": 5})
        searched.raise_for_status()
        body = searched.json()
        assert body["document_count"] > 0 and body["results"]
        print("Developer semantic search:", {"query": body["query"], "results": len(body["results"]),
              "entity_types": sorted({result["metadata"]["entity_type"] for result in body["results"]}),
              "document_ids": [result["document_id"] for result in body["results"]]}, flush=True)


if __name__ == "__main__":
    main()
