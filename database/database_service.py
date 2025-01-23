import json
import uuid

from fastapi import HTTPException

from api.dto import PostgreToVectorData, VectorDataQuery, DocumentRequest
from database.postgresql import get_prompt, get_all_prompt, insert_prompt, delete_prompt, get_data_rdb, \
    get_all_data_rdb, insert_vector_data, update_vector_data, delete_data_rdb
from database.vector_db import EmbeddingAPIClient


class DatabaseService:

    def get_all_prompt():
        return get_all_prompt()


    def get_prompt(self, node_nm: str, prompt_nm: str):
        return get_prompt(node_nm, prompt_nm)


    def add_prompt(node_nm: str, prompt_nm: str, prompt: str):
        return insert_prompt(node_nm, prompt_nm, prompt)


    def delete_prompt(node_nm: str, prompt_nm: str):
        return delete_prompt(node_nm, prompt_nm)




    def query_fewshot_vector(data: VectorDataQuery):
        return EmbeddingAPIClient.query_embedding(
            collection_name = data.collection_name,
            query_text = data.query_text,
            top_k = data.top_k
        )


    def get_all_fewshot_rdb():
        return get_all_data_rdb()


    def get_fewshot_rdb(data: PostgreToVectorData):
        return get_data_rdb(data)


    def get_all_fewshot_vector():
        return EmbeddingAPIClient.getAll_embedding()


    def get_fewshot_vector(title: str):
        return EmbeddingAPIClient.get_embedding(
            collection_name = title
        )


    def add_fewshot(title: str, content: str):
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
            # question text for vectorization
            documents.append(question)

            metadata = {
                "id": doc_id,
                "answer": shot["answer"]
            }
            if "date" in shot:
                metadata["date"] = shot["date"]
            if "stats" in shot:
                metadata["stats"] = shot["stats"]
            # SQL goes to metadata
            metadatas.append(metadata)

            success = insert_vector_data(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert vector data")
        print("Successfully inserted rdb data")

        EmbeddingAPIClient.add_embedding(
            collection_name=title,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted vector data")

        return success


    def addList_few_shot(title: str, shots: list[str]):
        ids = []
        documents = []  # question text for vectorization
        metadatas = []  # metadata including SQL

        for shot in shots:
            # Generate unique ID
            doc_id = str(uuid.uuid4())

            # Add to lists
            ids.append(doc_id)

            question = shot["question"]
            # question text for vectorization
            documents.append(question)

            metadata = {
                "id": doc_id,
                "answer": shot["answer"]
            }
            if "date" in shot:
                metadata["date"] = shot["date"]
            if "stats" in shot:
                metadata["stats"] = shot["stats"]
            # SQL goes to metadata
            metadatas.append(metadata)

            success = insert_vector_data(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert vector data")
        print("Successfully inserted rdb data")

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


    def collection_delete_fewshot(title: str):
        success = delete_data_rdb(title)
        print(f"Successfully deleted rdb data")

        EmbeddingAPIClient.collection_delete_embedding(
            collection_name=title,
        )
        print(f"Successfully deleted vector data")

        return success


    # def delete_few_shot(data: PostgreToVectorData):
    #     success = delete_data_rdb(data)
    #     if success:
    #         EmbeddingAPIClient.delete_embedding(
    #             collection_name=data.collection_name,
    #             item_id=data.item_id,
    #         )
    #     return success


    def restore_fewshot(data: PostgreToVectorData):
        dataList = {}

        for dataText in data:
            # print(f"dataText :::: {dataText}")

            collection_name = dataText["title"]
            id = dataText["id"]
            shot = dataText["shot"]
            document = shot["question"]
            metadata = {
                "id": id,
                "answer": shot["answer"]
            }
            if "date" in shot:
                metadata["date"] = shot["date"]
            if "stats" in shot:
                metadata["stats"] = shot["stats"]


            if collection_name not in dataList:
                dataList[collection_name] = DocumentRequest()

            # DocumentRequest 객체에 데이터 추가
            dataList[collection_name].ids.append(id)
            dataList[collection_name].documents.append(document)
            dataList[collection_name].metadatas.append(metadata)
            print(f"Data added to {collection_name}: id={id}, document={document}, metadata={metadata}")

        for collection in dataList:
            data = dataList[collection]
            # print(f"{collection} ::::::::::::: {data}")
            EmbeddingAPIClient.add_embedding(
                collection_name=collection,
                ids=data.ids,
                documents=data.documents,
                metadatas=data.metadatas
            )

        print("Successfully restored vector data")