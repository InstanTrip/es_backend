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

    not_found_count = 0
    for i in data.ids:
        # id값이 -1 인 경우 개수
        if i.id == "-1":
            not_found_count += 1

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
        if len(i["hits"]["hits"]) <= 0:
            continue

        temp = i["hits"]["hits"][0]["_source"]
        temp["type"] = i["hits"]["hits"][0]["_index"]

        if temp.get("title_vector"):
            del temp["title_vector"]
        if temp.get("category_vector"):
            del temp["category_vector"]
        if temp.get("description_vector"):
            del temp["description_vector"]
        
        # id값을 string으로 변환
        if temp.get("id"):
            temp["id"] = str(temp["id"])
        
        if temp["type"] == "elastic_restaurant":
            # 이미지 데이터 가공
            if temp.get("image"):
                tmp_img = []
                for img in temp["image"]:
                    tmp_img.append("https://www.bluer.co.kr" + img)
                temp["image"] = tmp_img
        
        return_data.append(temp)

    for i in range(not_found_count):
        return_data.append(
            {
                "type": data.ids[i].type,
                "id": data.ids[i].id,
                "title": "찾을 수 없어요",
                "description": "",
                "image": [],
                "address": "",
                "location": {
                    "lat": 0.0,
                    "lon": 0.0
                }
            }
        )

    # data와 순서 맞추기
    return_data_sorted = []
    for i in data.ids:
        for j in return_data:
            if i.type == j["type"] and i.id == j["id"]:
                return_data_sorted.append(j)
                break




    await es_client.close()

    return return_data_sorted