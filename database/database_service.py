import json
import uuid

from fastapi import HTTPException

from api.dto import PostgreToVectorData, VectorDataQuery, DocumentRequest, MappingRequest, VocRequest, RecommendRequest, \
    RecommendCtgryRequest, StockRequest
from database.postgresql import get_all_prompt, get_prompt, insert_prompt, delete_prompt, get_all_fewshot_rdb, \
    get_fewshot_rdb, insert_fewshot_rdb, delete_fewshot_rdb, get_all_mapping, get_mapping, insert_mapping, \
    update_mapping, delete_mapping, get_all_voc, get_voc, insert_voc, update_voc, delete_voc, answer_voc, \
    get_home_recommend, get_all_recommend, get_recommend, insert_recommend, update_recommend, delete_recommend, \
    get_all_recommend_ctgry, get_recommend_ctgry, insert_recommend_ctgry, update_recommend_ctgry, \
    delete_recommend_ctgry, get_all_stock, insert_stock, delete_stock
from database.vector_db import EmbeddingAPIClient


class DatabaseService:

    #####  /prompt  #####

    def get_all_prompt():
        return get_all_prompt()


    def get_prompt(self, node_nm: str, prompt_nm: str):
        return get_prompt(node_nm, prompt_nm)


    def add_prompt(node_nm: str, prompt_nm: str, prompt: str):
        return insert_prompt(node_nm, prompt_nm, prompt)


    def delete_prompt(node_nm: str, prompt_nm: str):
        return delete_prompt(node_nm, prompt_nm)




    #####  /fewshot  #####

    def query_fewshot_vector(data: VectorDataQuery):
        return EmbeddingAPIClient.query_embedding(
            collection_name = data.collection_name,
            query_text = data.query_text,
            top_k = data.top_k
        )


    def get_all_fewshot_vector():
        return EmbeddingAPIClient.getAll_embedding()


    def get_fewshot_vector(collectionName: str):
        return EmbeddingAPIClient.get_embedding(
            collection_name = collectionName
        )


    def get_all_fewshot_rdb():
        return get_all_fewshot_rdb()


    def get_fewshot_rdb(data: PostgreToVectorData):
        return get_fewshot_rdb(data)


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

            success = insert_fewshot_rdb(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert Fewshot rdb data")
        print("Successfully inserted Fewshot rdb data")

        EmbeddingAPIClient.add_embedding(
            collection_name=title,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted Fewshot vector data")

        return success


    def add_fewshot_list(title: str, shots: list[str]):
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

            success = insert_fewshot_rdb(PostgreToVectorData(title=title, shot=json.dumps(shot, ensure_ascii=False), id=doc_id))
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert Fewshot rdb data")
        print("Successfully inserted Fewshot rdb data")

        EmbeddingAPIClient.add_embedding(
            collection_name=title,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print("Successfully inserted Fewshot vector data")

        return success


    def collection_delete_fewshot(title: str):
        success = delete_fewshot_rdb(title)
        print(f"Successfully deleted Fewshot rdb data")

        EmbeddingAPIClient.collection_delete_embedding(
            collection_name=title,
        )
        print(f"Successfully deleted Fewshot vector data")

        return success


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




    #####  /mapping  #####

    def get_all_mapping():
        return get_all_mapping()


    def get_mapping(idx: int):
        return get_mapping(idx)


    def insert_mapping(data: MappingRequest):
        return insert_mapping(data)


    def update_mapping(data: MappingRequest):
        return update_mapping(data)


    def delete_mapping(idx: int):
        return delete_mapping(idx)




    #####  /voc  #####

    def get_all_voc():
        return get_all_voc()


    def get_voc(seq: int):
        return get_voc(seq)


    def insert_voc(data: VocRequest):
        return insert_voc(data)


    def update_voc(data: VocRequest):
        return update_voc(data)


    def delete_voc(seq: int):
        return delete_voc(seq)


    def answer_voc(data: VocRequest):
        return answer_voc(data)




    #####  /recommend  #####

    def get_home_recommend():
        return get_home_recommend()


    def get_all_recommend():
        return get_all_recommend()


    def get_recommend(seq: int):
        return get_recommend(seq)


    def insert_recommend(data: RecommendRequest):
        return insert_recommend(data)


    def update_recommend(data: RecommendRequest):
        return update_recommend(data)


    def delete_recommend(seq: int):
        return delete_recommend(seq)




    def get_all_recommend_ctgry():
        return get_all_recommend_ctgry()


    def get_recommend_ctgry(ctgryCd: str):
        return get_recommend_ctgry(ctgryCd)


    def insert_recommend_ctgry(data: RecommendCtgryRequest):
        return insert_recommend_ctgry(data)


    def update_recommend_ctgry(data: RecommendCtgryRequest):
        return update_recommend_ctgry(data)


    def delete_recommend_ctgry(ctgryCd: str):
        return delete_recommend_ctgry(ctgryCd)



    #####  /stock  #####

    def get_all_stock():
        return get_all_stock()


    def get_stock(stockCd: str):
        return get_stock(stockCd)


    def insert_stock(data: StockRequest):
        return insert_stock(data)


    def insert_stock_list(data: StockRequest):
        for stockNickNm in data.stockNickNmList:
            data["stockNickNm"] = stockNickNm
            success = DatabaseService.insert_stock(data)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to insert stock data")
        return success


    def delete_stock(stockCd: str):
        return delete_stock(stockCd)