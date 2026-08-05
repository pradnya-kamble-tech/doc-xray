import sqlite3
from fastapi.testclient import TestClient
from main import app

def test_api():
    try:
        conn = sqlite3.connect("data/docxray.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        doc_id = row[0] if row else "fake-id"
    except Exception as e:
        print("Could not load db:", e)
        doc_id = "fake-id"
        
    print(f"Testing with doc_id: {doc_id}")

    with TestClient(app) as client:
        # test fallback
        resp = client.post(f"/api/chat/fake-doc-123", json={"message": "What is the capital of Paris?"})
        print("Fallback test status:", resp.status_code)
        print("Fallback test resp:", resp.json())

        # test real doc
        if doc_id != "fake-id":
            resp = client.post(f"/api/chat/{doc_id}", json={"message": "Please summarize this document."})
            print("Real test status:", resp.status_code)
            try:
                print("Real test resp:", resp.json())
            except Exception as e:
                print("Error parsing real text:", e)
                print("Real test text:", resp.text)
        else:
            print("No real documents to test")

if __name__ == "__main__":
    test_api()
