import json
import uuid

from fastapi import HTTPException

from data_class.request import PostgreToVectorData, VectorDataQuery
from database.postgresql import get_prompt, get_all_prompt, insert_prompt, delete_prompt, get_vector_data, getAll_vector_data, insert_vector_data, update_vector_data, delete_vector_data
from database.vector_db import EmbeddingAPIClient


class DatabaseService:

    def get_prompt(self, node_nm: str, prompt_nm: str):
        return get_prompt(node_nm, prompt_nm)


    def get_all_prompt():
        return get_all_prompt()


    def add_prompt(node_nm: str, prompt_nm: str, prompt: str):
        return insert_prompt(node_nm, prompt_nm, prompt)


    def delete_prompt(node_nm: str, prompt_nm: str):
        return delete_prompt(node_nm, prompt_nm)




    def query_vector_few_shot(data: VectorDataQuery):
        return EmbeddingAPIClient.query_embedding(
            collection_name = data.collection_name,
            query_text = data.query_text,
            top_k = data.top_k
        )


    def get_postgre_few_shot(data: PostgreToVectorData):
        return get_vector_data(data)


    def getAll_postgre_few_shot():
        return getAll_vector_data()


    def getTitleList_vector_few_shot():
        return EmbeddingAPIClient.getTitleList_embedding()


    def get_vector_few_shot(title: str):
        return EmbeddingAPIClient.get_embedding(
            collection_name = title
        )


    def getAll_vector_few_shot():
        return EmbeddingAPIClient.getAll_embedding()


    def add_few_shot(title: str, content: str):
        ids = []
        documents = []  # question text for vectorization
        metadatas = []  # metadata including SQL

        shots = json.loads(content)
        for shot in shots:
            # Generate unique ID
            doc_id = str(uuid.uuid4())

            # Add to lists
            ids.append(doc_id)

            question = shot["question"]
            documents.append(question)  # question text for vectorization

            metadata = {
                "id": doc_id,
                "answer": shot["answer"]  # SQL goes to metadata
            }
            metadatas.append(metadata)

            success = insert_vector_data(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert vector data")

        EmbeddingAPIClient.add_embedding(
            collection_name=title,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted vector data")
        return success


    def add_few_shot2(title: str, shots: list[str]):
        ids = []
        documents = []  # question text for vectorization
        metadatas = []  # metadata including SQL

        for shot in shots:
            # Generate unique ID
            doc_id = str(uuid.uuid4())

            # Add to lists
            ids.append(doc_id)

            question = shot["question"]
            documents.append(question)  # question text for vectorization

            metadata = {
                "id": doc_id,
                "answer": shot["answer"]  # SQL goes to metadata
            }
            metadatas.append(metadata)

            success = insert_vector_data(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert vector data")

        EmbeddingAPIClient.add_embedding(
            collection_name=title,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted vector data")
        return success


    def update_few_shot(data : PostgreToVectorData):
        success = update_vector_data(data)
        if success:
            EmbeddingAPIClient.update_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
                document=data.document
            )
        return success


    # def delete_few_shot(data: PostgreToVectorData):
    #     success = delete_vector_data(data)
    #     if success:
    #         EmbeddingAPIClient.delete_embedding(
    #             collection_name=data.collection_name,
    #             item_id=data.item_id,
    #         )
    #     return success


    def multi_delete_few_shot(title: str):
        ids = []

        resultList = get_vector_data(title)
        for result in resultList:
            # Add to lists
            ids.append(result["id"])

        success = delete_vector_data(title)
        if success:
            print(f"Successfully deleted postgreSQL data")

            EmbeddingAPIClient.multi_delete_embedding(
                collection_name=title,
                ids=ids,
            )

        return success