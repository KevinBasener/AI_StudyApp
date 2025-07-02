import os
import requests

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL")
if not BACKEND_URL:
    raise ValueError("BACKEND_URL is not set in the .env file")


class DocumentManager:
    """Handles document uploads and searches."""

    def upload_pdfs(self, file_names):
        """Uploads PDFs to the backend one by one and returns a list of document IDs."""
        doc_ids = []
        for file_name in file_names:
            with open(file_name, "rb") as file:
                response = requests.post(
                    f"{BACKEND_URL}/api/documents/upload",
                    files={"file": file},
                )

            if response.status_code == 200:
                doc_info = response.json()
                if "document_id" in doc_info:
                    doc_ids.append(doc_info["document_id"])
                else:
                    raise Exception(f"Unexpected response: {response.text}")
            else:
                raise Exception(f"Upload failed for {file_name}: {response.text}")

        return doc_ids

    def search_documents(self, query):
        """Searches for documents in the backend."""
        response = requests.get(f"{BACKEND_URL}/api/documents/search", params={"query": query})
        if response.status_code == 200:
            return response.json().get("documents", [])
        else:
            raise Exception(f"Document search failed: {response.text}")
