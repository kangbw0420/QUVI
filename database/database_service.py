import json
import uuid

from fastapi import HTTPException

from data_class.request import PostgreToVectorData, VectorDataQuery
from database.postgresql import get_all_prompt, get_prompt, insert_prompt, getAll_vector_data, get_vector_data, \
    insert_vector_data, update_vector_data, delete_vector_data
from database.vector_db import EmbeddingAPIClient

# vector 연결
vector_client = EmbeddingAPIClient()

class DatabaseService:

    def test_get_few_shot(self, collection_name: str):
        return vector_client.test_embedding(
            collection_name=collection_name
        )

    def add_few_shot(self, data : PostgreToVectorData):
        ids = []
        documents = []  # question text for vectorization
        metadatas = []  # metadata including SQL

        dataList = json.loads(data.document)
        for dataText in dataList:
            # Generate unique ID
            doc_id = str(uuid.uuid4())

            # Add to lists
            ids.append(doc_id)

            question = dataText["question"]
            documents.append(question)  # question text for vectorization

            metadata = {
                "id": doc_id,
                "answer": dataText["answer"]  # SQL goes to metadata
            }
            metadatas.append(metadata)

            success = insert_vector_data(PostgreToVectorData(collection_name=data.collection_name, id=doc_id, document=json.dumps(dataText, ensure_ascii=False)))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert vector data")

        vector_client.add_embedding(
            collection_name=data.collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted vector data")

        return success

    def update_few_shot(self, data : PostgreToVectorData):
        success = update_vector_data(data)
        if success:
            vector_client.update_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
                document=data.document
            )
        return success

    def get_vector_few_shot(self, data : VectorDataQuery):
        return vector_client.query_embedding(
            collection_name=data.collection_name,
            query_text = data.query_text,
            top_k = data.top_k # 조회할 건수 기본 1건
        )

    def getAll_postgre_few_shot(self):
        return getAll_vector_data()

    def get_postgre_few_shot(self, data: PostgreToVectorData):
        return get_vector_data(data)

    def multi_delete_few_shot(self, data : PostgreToVectorData):
        ids = []

        resultList = get_vector_data(data)
        for result in resultList:
            # Add to lists
            ids.append(result["id"])

        success = delete_vector_data(data)
        if success:
            vector_client.multi_delete_embedding(
                collection_name=data.collection_name,
                ids=ids,
            )
        return success

    def delete_few_shot(self, data: PostgreToVectorData):
        success = delete_vector_data(data)
        if success:
            vector_client.delete_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
            )
        return success

    def add_prompt(self, node_nm: str, prompt_nm: str, prompt: str):
        return insert_prompt(node_nm, prompt_nm, prompt)

    def get_all_prompt(self):
        return get_all_prompt()

    def get_prompt(self, node_nm: str, prompt_nm: str):
        return get_prompt(node_nm, prompt_nm)