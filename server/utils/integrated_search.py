from elasticsearch import AsyncElasticsearch

from server import ES_HOST, ES_PORT
from server import vectorizer


async def integrated_search(query: str, lat: float, lon: float):
    """
    통합 검색
    """
    es = AsyncElasticsearch(f"http://{ES_HOST}:{ES_PORT}")

    # 검색 쿼리
    search_query = {
        "size": 30,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": []
                    }
                },
                "functions": [],
                "score_mode": "sum",  # 함수 점수 합산 방식
                "boost_mode": "sum"   # 기존 점수와 합산
            }
        }
    }

    if lat and lon:
            search_query["query"]["function_score"]["functions"].append({
                "gauss": {
                    "location": {
                        "origin": {"lat": lat, "lon": lon},
                        "offset": "2km",  # 2km부터 점수 감소 시작
                        "scale": "5km"    # 5km 지점에서 최대 감소
                    }
                },
                "weight": 15  # 거리 가중치 비율
            })

    vector_query = vectorizer.vectorize(query)

    # 텍스트 검색 조건 추가
    search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
        {
            "match": {
                "description": {
                    "query": query,
                    "boost": 5  # 설명 필드 가중치
                }
            }
        },
        {
            "match": {
                "title": {
                    "query": query,
                    "boost": 5  # 제목 필드 가중치
                }
            }
        }
    ])

    # knn
    search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
        {
            "knn": {
                "field": "description_vector",
                "query_vector": vector_query,
                "num_candidates": 100,
                "boost": 9
            }
        },
        {
            "knn": {
                "field": "title_vector",
                "query_vector": vector_query,
                "num_candidates": 100,
                "boost": 7
            }
        }
    ])
        
    if not search_query["query"]["function_score"]["query"]["bool"]["should"]:
        del search_query["query"]["function_score"]["query"]["bool"]["should"]
    

    # 검색 실행
    index_list = [
        "elastic_restaurant",
        "elastic_destination",
        "elastic_accommodation"
    ]
    body = []
    for index in index_list:
        body.extend([
            {"index": index},
            search_query
        ])
    response = await es.msearch(
        index="index",
        body=body
    )

    # 리턴 데이터 가공
    # 제목, 이미지, 주소, 우편번호, id값만 가져오기
    return_data = []
    for i in response["responses"]:
        for j in i["hits"]["hits"]:
            temp = j["_source"]
            data_id = j["_id"]
            data_title = temp.get("title")
            data_image = temp.get("image")
            if not data_image:
                data_image = temp.get("images")
            
            if data_image and type(data_image) != list:
                data_image = [data_image]
            
            data_address = temp.get("address")

            data_postal_code = temp.get("postal_code")

            return_data.append({
                "index": j["_index"],
                "id": data_id,
                "title": data_title,
                "image": data_image,
                "address": data_address,
                "postal_code": data_postal_code,
                "score": j["_score"]
            })
    
    # 스코어값 기준 정렬
    return_data = sorted(return_data, key=lambda x: x["score"], reverse=True)

    await es.close()
    return return_data