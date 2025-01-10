'''
from database.postgresql import execute_query, get_all_prompt, insert_prompt, get_vector_data, insert_vector_data, update_vector_data
from database.vector_db import EmbeddingAPIClient
from data_class.request import PostgreToVectorData, VectorDataQuery

# vector 연결
vector_client = EmbeddingAPIClient()

class DatabaseService:
    @staticmethod
    def add_few_shot(data : PostgreToVectorData):
        success = insert_vector_data(data)

        if success:
            vector_client.add_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
                text=data.text
            )

        return success

    @staticmethod
    def update_few_shot(data : PostgreToVectorData):
        success = update_vector_data(data)
        if success:
            vector_client.update_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
                text=data.text
            )
        return success

    @staticmethod
    def get_vector_few_shot(data : VectorDataQuery):
        return vector_client.query_embedding(
            collection_name=data.collection_name,
            query_text = data.query_text,
            top_k = data.top_k # 조회할 건수 기본 1건
        )

    @staticmethod
    def get_postgre_few_shot(data: PostgreToVectorData):
        return get_vector_data(data)


    @staticmethod
    def delete_few_shot(data : PostgreToVectorData):
        success = update_vector_data(data)
        if success:
            vector_client.delete_embedding(
                collection_name=data.collection_name,
                item_id=data.item_id,
            )
        return success

    @staticmethod
    def add_prompt(node_nm: str, prompt_nm: str, prompt: str):
        return insert_prompt(node_nm, prompt_nm, prompt)

    @staticmethod
    def get_all_prompt():
        return get_all_prompt()

    # @staticmethod
    # def get_prompt(prompt_nm: str):
    #     return get_prompt(prompt_nm)
'''