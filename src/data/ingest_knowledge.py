# This script is responsible for converting whole merged medical diseases data into the vector embeddings and store it in the Chroma vector store.

import json
import os
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def create_vector_db(json_file_path:str, persist_directory: str):

    # 1. Loads the raw json data
    if not os.path.exists(json_file_path):
        raise FileNotFoundError("Cannot find the filepath. Check the filepath again")
    
    with open(json_file_path, "r", encoding = 'utf-8') as file:
        dieases_data = json.load(file)

    documents = []

    # 2. Iterate through each disease record in the merged json file
    for entry in dieases_data:
        disease_name = entry.get("Disease","Unknown")
        category = entry.get("Category","Unknown")
        url = entry.get("Source URL", "Unknown")

        # 3. Defining the page content for each disease record
        content_parts = [
            f"Disease: {disease_name}",
            f"Category: {category}",
            f"Overview: {entry.get('Overview', '')}",
            f"Symptoms: {entry.get('Symptoms', '')}",
            f"Causes: {entry.get('Causes', '')}",
            f"Risk Factors: {entry.get('Risk Factors', '')}",
            f"Complications: {entry.get('Complications', '')}"
        ]
        page_content = "\n".join(content_parts)

        # 4. Defining the metadata for each disease record
        metadata = {
            "disease": disease_name,
            "category": category,
            "url": url
        }

        # 5. Create a document out of all the page_content and the metadata as the langchain and ChromaDB require the data to be in the form of a document
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)

    print(f"Loaded {len(documents)} diseases. Initializing the HuggingFaceEmbeddings model")

    # 6. Initialize the HuggingFaceEmbeddings model to convert the documents into vector embeddings
    embeddings = HuggingFaceEmbeddings(model_name = "all-MiniLM-L6-v2")

    print(f"Building ChromaDB vector store at '{persist_directory}'.....")

    # 7. Create a Chroma vector store from the documents and embeddings, and save the vector store/database in the persist directory
    vector_store = Chroma.from_documents(
        documents = documents,
        embedding = embeddings,
        persist_directory = persist_directory
    )

    print("ChromaDB vector store built successfully")

if __name__ == "__main__":
    # Define the paths to the JSON file and the persist directory where chroma vector database needs to be stored
    JSON_PATH = "src/data/merged_medical_data.json"
    DB_DIR = "chroma_db"

    create_vector_db(JSON_PATH,DB_DIR)