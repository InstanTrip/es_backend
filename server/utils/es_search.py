import random
import datetime

from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

from server import vectorizer
from server import ES_HOST, ES_PORT
from server import LOGGER

class ElasticSearch:
    def __init__(self, date: datetime.datetime, query: list = []) -> None:
        # ES
        self.elastic_client = None

        # 지역
        self.region = ""

        # 쿼리 - 유저 취향
        self.query = query
        self.query_vector = []

        # 벡터화 모델
        self.vectorizer = vectorizer
        
        # 중복 방지용
        self.accommodation_list = []
        self.restaurant_list = []
        self.destination_list = []

        # 최적화 위한 쿼리저장
        self.accommodation_query = []
        self.restaurant_query = []
        self.destination_query = []

        self.accommodation_query_vector = []
        self.restaurant_query_vector = []
        self.destination_query_vector = []

        # 타겟 날짜
        self.target_date = date

        # 같은날 검색 횟수 카운트
        self.search_count = 0
    
    def set_query(self, query_category: str, query: list) -> None:
        """ 쿼리 설정 """
        if query_category == "accommodation":
            self.accommodation_query = query
            self.accommodation_query_vector = [self.vectorizer.vectorize(q) for q in query]
        elif query_category == "restaurant":
            self.restaurant_query = query
            self.restaurant_query_vector = [self.vectorizer.vectorize(q) for q in query]
        elif query_category == "destination":
            self.destination_query = query
            self.destination_query_vector = [self.vectorizer.vectorize(q) for q in query]
        else:
            LOGGER.error("Invalid query category")

    def connect_es(self) -> None:
        # elasticsearch 연결
        LOGGER.info("Elasticsearch 연결 중...")
        
        self.elastic_client = Elasticsearch(f"http://{ES_HOST}:{ES_PORT}")
        
        LOGGER.info(self.elastic_client.info())
        LOGGER.info("Elasticsearch 연결 완료")
    
    def disconnect_es(self) -> None:
        # elasticsearch 연결 해제
        if self.elastic_client:
            self.elastic_client.close()
            LOGGER.info("Elasticsearch 연결 해제")
        else:
            LOGGER.error("Elasticsearch 연결이 되어 있지 않습니다.")

    def set_region(self, region: str) -> None:
        """ 지역 설정 """
        self.region = region
    
    def next_day(self) -> None:
        """ 다음날로 설정 """
        self.target_date = self.target_date + datetime.timedelta(days=1)
        self.search_count = 0

    def accommodation_search(self, lat: float = 0, lon: float = 0) -> dict:
        """ 숙소 검색 """
        # 카테고리: 인덱스 이름
        # 쿼리: 검색 태그 여러개
        # 
        # self.region
    
        search_query = {
            "size": 30,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "filter": [
                                {"match_phrase": {"address": self.region}}
                            ],
                            "should": []
                        }
                    },
                    "functions": [],
                    "score_mode": "sum",  # 함수 점수 합산 방식
                    "boost_mode": "sum"   # 기존 점수와 합산
                }
            }
        }

        # 텍스트 검색 조건 추가
        for query_text in self.accommodation_query:
            if not query_text:
                continue

            search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                {
                    "match": {
                        "description": {
                            "query": query_text,
                            "boost": 5  # 설명 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "title": {
                            "query": query_text,
                            "boost": 3  # 제목 필드 가중치
                        }
                    }
                }
            ])

        # 거리 기준 정렬 조건
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

        # knn
        if self.accommodation_query_vector:
            for vec in self.accommodation_query_vector:
                search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                    {
                        "knn": {
                            "field": "description_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 9
                        }
                    },
                    {
                        "knn": {
                            "field": "title_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 7
                        }
                    }
                ])
        
        if not search_query["query"]["function_score"]["query"]["bool"]["should"]:
            del search_query["query"]["function_score"]["query"]["bool"]["should"]

        # 테스트 검색 후 출력
        res = self.elastic_client.search(index="elastic_accommodation", body=search_query)
        LOGGER.info(f"검색 속도: {res['took']}ms")
        # for i in res["hits"]["hits"]:
        #     # print(i)
        #     print(f"{i['_score']}점 {i['_source']['title']}")

    
        # 순서대로 선택, 중복제거, 중복값은 id만 넣고 비교
        pick_res = None
        for i in res["hits"]["hits"]:
            # 중복 방지
            if i["_id"] in self.restaurant_list:
                continue
            self.restaurant_list.append(i["_id"])

            pick_res = i
        
        if not pick_res and res["hits"]["hits"]:
            # 전부 중복일 경우 적당히 랜덤으로 선택
            pick_res = random.choice(res["hits"]["hits"])
            
        return_data = {
            "id": str(pick_res["_id"]),
            "lat": pick_res["_source"]["location"]["lat"],
            "lon": pick_res["_source"]["location"]["lon"],
        }

        return return_data
    

    def destination_search(self, lat: float = 0, lon: float = 0) -> dict:
        """ 여행지 검색 """
        # 카테고리: 인덱스 이름
        # 쿼리: 검색 태그 여러개
        # 
        # self.region

        self.search_count += 1

        tg = self.target_date.strftime('%Y-%m-%d')

        today_month = int(tg.split("-")[1])
        today_day = int(tg.split("-")[2])

        search_query = {
            "size": 30,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "filter": [
                                {"match_phrase": {"address": self.region}},
                                {  # 날짜 필터 추가
                                    "bool": {
                                        "should": [
                                            {   # 조건 1: 이벤트 기간 내
                                                "script": {
                                                    "script": {
                                                        "source": """
                                                            // 날짜 필드 존재 여부 확인
                                                            if (doc['event_start_date'].size() == 0 
                                                              || doc['event_end_date'].size() == 0) {
                                                                return false;
                                                            }
                                                            // 날짜 파싱
                                                            def start = doc['event_start_date'].value.toInstant()
                                                              .atZone(ZoneId.of('UTC')).toLocalDate();
                                                            def end = doc['event_end_date'].value.toInstant()
                                                              .atZone(ZoneId.of('UTC')).toLocalDate();
                                                            // 월/일 추출
                                                            int currM = params.today_m;
                                                            int currD = params.today_d;
                                                            int startM = start.getMonthValue();
                                                            int startD = start.getDayOfMonth();
                                                            int endM = end.getMonthValue();
                                                            int endD = end.getDayOfMonth();
                                                            // 월별 범위 비교
                                                            if (startM <= endM) {
                                                                // 일반 범위 (예: 3월5일~5월10일)
                                                                return (currM >= startM && currM <= endM) 
                                                                  && !(currM == startM && currD < startD) 
                                                                  && !(currM == endM && currD > endD);
                                                            } else {
                                                                // 연도 경계 범위 (예: 12월20일~1월5일)
                                                                return (currM >= startM || currM <= endM) 
                                                                  && !(currM == startM && currD < startD) 
                                                                  && !(currM == endM && currD > endD);
                                                            }
                                                        """,
                                                        "params": {
                                                            "today_m": today_month,
                                                            "today_d": today_day
                                                        }
                                                    }
                                                }
                                            },
                                            {  # 조건 2: start_date와 end_date가 모두 없음
                                                "bool": {
                                                    "must_not": [
                                                        {"exists": {"field": "event_start_date"}},
                                                        {"exists": {"field": "event_end_date"}}
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            ],
                            "should": []
                        }
                    },
                    "functions": [],
                    "score_mode": "sum",  # 함수 점수 합산 방식
                    "boost_mode": "sum"   # 기존 점수와 합산
                }
            }
        }

        # 텍스트 검색 조건 추가
        for query_text in self.destination_query:
            if not query_text:
                continue

            search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                {
                    "match": {
                        "description": {
                            "query": query_text,
                            "boost": 5  # 설명 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "title": {
                            "query": query_text,
                            "boost": 4  # 제목 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "type": {
                            "query": query_text,
                            "boost": 5
                        }
                    }
                }
            ])

        # 거리 기준 정렬 조건
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

        # knn
        if self.destination_query_vector:
            for vec in self.destination_query_vector:
                search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                    {
                        "knn": {
                            "field": "description_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 9
                        }
                    },
                    {
                        "knn": {
                            "field": "title_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 7
                        }
                    }
                ])
        
        # 야간 여행지 검색 조건 추가
        if self.search_count <= 5:
            search_query["query"]["function_score"]["query"]["bool"]["must_not"] = [{
                "match_phrase": {
                    "title": "천문대"
                }
            }]

        if not search_query["query"]["function_score"]["query"]["bool"]["should"]:
            del search_query["query"]["function_score"]["query"]["bool"]["should"]

        print(len(str(search_query)))

        # 테스트 검색 후 출력
        res = self.elastic_client.search(index="elastic_destination", body=search_query)
        # print(len(res["hits"]["hits"]))
        LOGGER.info(f"검색 속도: {res['took']}ms")
        # for i in res["hits"]["hits"]:
        #     # print(i)
        #     print(f"{i['_score']}점 {i['_source']['title']}")

        # 순서대로 선택, 중복제거, 중복값은 id만 넣고 비교
        pick_res = None
        for i in res["hits"]["hits"]:
            # 중복 방지
            if i["_id"] in self.restaurant_list:
                continue
            self.restaurant_list.append(i["_id"])

            pick_res = i
        
        if not pick_res and res["hits"]["hits"]:
            # 전부 중복일 경우 적당히 랜덤으로 선택
            pick_res = random.choice(res["hits"]["hits"])
            
        return_data = {
            "id": str(pick_res["_id"]),
            "lat": pick_res["_source"]["location"]["lat"],
            "lon": pick_res["_source"]["location"]["lon"],
        }

        return return_data

    def restaurant_search(self, lat: float = 0, lon: float = 0) -> dict:
        """ 식당 검색 """
        # 카테고리: 인덱스 이름
        # 쿼리: 검색 태그 여러개
        # 
        # self.region

        self.search_count += 1
    
        search_query = {
            "size": 30,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "filter": [
                                {
                                    "match_phrase": {
                                        "address": self.region
                                    },
                                },
                                {
                                    "match_phrase": {
                                        "status": "영업"
                                    },
                                }
                            ],
                            "should": []
                        }
                    },
                    "functions": [],
                    "score_mode": "sum",  # 함수 점수 합산 방식
                    "boost_mode": "sum"   # 기존 점수와 합산
                }
            }
        }

        # 텍스트 검색 조건 추가
        for query_text in self.restaurant_query:
            if not query_text:
                continue

            search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                {
                    "match": {
                        "description": {
                            "query": query_text,
                            "boost": 9  # 설명 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "title": {
                            "query": query_text,
                            "boost": 9  # 제목 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "category": {
                            "query": query_text,
                            "boost": 9  # 제목 필드 가중치
                        }
                    }
                },
                {
                    "match": {
                        "menu": {
                            "query": query_text,
                            "boost": 9  # 제목 필드 가중치
                        }
                    }
                },
            ])

        # 거리 기준 정렬 조건
        if lat and lon:
            search_query["query"]["function_score"]["functions"].append({
                "gauss": {
                    "location": {
                        "origin": {"lat": lat, "lon": lon},
                        "offset": "2km",  # 2km부터 점수 감소 시작
                        "scale": "5km"    # 5km 지점에서 최대 감소
                    }
                },
                "weight": 8  # 거리 가중치 비율
            })

        search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
            {
                "term": {
                    "ribbon_count": {
                        "value": 0,
                        "boost": 1
                    }
                }
            },
            {
                "term": {
                    "ribbon_count": {
                        "value": 1,
                        "boost": 1
                    }
                }
            },
            {
                "term": {
                    "ribbon_count": {
                        "value": 2,
                        "boost": 4
                    }
                }
            },
            {
                "term": {
                    "ribbon_count": {
                        "value": 3,
                        "boost": 7
                    }
                }
            }
        ])

        # knn
        if self.restaurant_query_vector:
            for vec in self.restaurant_query_vector:
                search_query["query"]["function_score"]["query"]["bool"]["should"].extend([
                    {
                        "knn": {
                            "field": "description_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 8
                        }
                    },
                    {
                        "knn": {
                            "field": "category_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 8
                        }
                    },
                    {
                        "knn": {
                            "field": "title_vector",
                            "query_vector": vec,
                            "num_candidates": 100,
                            "boost": 8
                        }
                    }
                ])
        
        if not search_query["query"]["function_score"]["query"]["bool"]["should"]:
            del search_query["query"]["function_score"]["query"]["bool"]["should"]

        # 테스트 검색 후 출력
        res = self.elastic_client.search(index="elastic_restaurant", body=search_query)
        # print(len(res["hits"]["hits"]))
        LOGGER.info(f"검색 속도: {res['took']}ms")
        # for i in res["hits"]["hits"]:
        #     # print(i)
        #     print(f"{i['_score']}점 {i['_source']['title']} | 블루리본 {i['_source']['ribbon_count']}개")
        

        # 순서대로 선택, 중복제거, 중복값은 id만 넣고 비교
        pick_res = None
        for i in res["hits"]["hits"]:
            # 중복 방지
            if i["_id"] in self.restaurant_list:
                continue
            self.restaurant_list.append(i["_id"])

            pick_res = i
        
        if not pick_res and res["hits"]["hits"]:
            # 전부 중복일 경우 적당히 랜덤으로 선택
            pick_res = random.choice(res["hits"]["hits"])
        
        return_data = {
            "id": str(pick_res["_id"]),
            "lat": pick_res["_source"]["location"]["lat"],
            "lon": pick_res["_source"]["location"]["lon"],
        }

        return return_data

if __name__ == "__main__":
    today = datetime.datetime.today()
    # ES 연결
    es = ElasticSearch(today)
    es.connect_es()

    # 검색
    # es.accommodation_search(["안락한"], 36.5509, 128.7313)
    # es.restaurant_search(["짬뽕", "짜장면"], 36.5509, 128.7313)
    es.destination_search(["래프팅"], 36.5509, 128.7313)