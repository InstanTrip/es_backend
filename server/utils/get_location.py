import time
import asyncio
from elasticsearch import AsyncElasticsearch

from server.models.locations import LocationList
from server import ES_HOST, ES_PORT

async def get_location(data: LocationList):
    """
    id기반 여행지 데이터 가져오기
    """
    es_client = AsyncElasticsearch(f"http://{ES_HOST}:{ES_PORT}")

    # data = [
    #     {"type": "elastic_restaurant", "id": "5070000-101-2001-00635"},
    #     {"type": "elastic_destination", "id": "11519"},
    #     {"type": "elastic_restaurant", "id": "5070000-101-2004-00238"}
    # ]

    queries = {
        "elastic_restaurant": [],
        "elastic_destination": [],
        "elastic_accommodation": []
    }
    for i in data.ids:
        queries[i.type].append({
            "size": 1,
            "query": {
                "match": {
                    "id": i.id
                }
            }
        })

    body = []
    for i in queries:
        for j in queries[i]:
            body.extend([
                {"index": i},
                j
            ])

    response = await es_client.msearch(
        index="index",
        body=body
    )

    # 리턴 데이터 가공
    # 벡터값 제거
    return_data = []
    for i in response["responses"]:
        temp = i["hits"]["hits"][0]["_source"]
        if temp.get("title_vector"):
            del temp["title_vector"]
        if temp.get("category_vector"):
            del temp["category_vector"]
        if temp.get("description_vector"):
            del temp["description_vector"]
        
        # id값을 string으로 변환
        if temp.get("id"):
            temp["id"] = str(temp["id"])
        
        return_data.append(temp)
    
    # data와 순서 맞추기
    return_data = sorted(return_data, key=lambda x: data.ids.index({"type": x["destination_type"], "id": x["id"]}))
    
    await es_client.close()

    return return_data