import datetime
from fastapi import APIRouter, Depends
from elasticsearch import Elasticsearch

from server.models.create_trip import CreateTripData
from server.utils.es_search import ElasticSearch
from server.utils.city import citys, city_with_coordinate_dict
from server.utils.optimal_route import optimal_route_bruteforce

router = APIRouter(prefix="")

@router.post("/create-trip/")
async def create_trip(data: CreateTripData):
    """
    여행 계획 생성
    """
    start_date = datetime.datetime.strptime(data.start_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(data.end_date, "%Y-%m-%d")

    # 시작날과 종료일 사이 날짜 리스트 생성
    date_list = []
    temp_date = start_date
    while temp_date <= end_date:
        date_list.append(temp_date.strftime("%Y-%m-%d"))
        temp_date += datetime.timedelta(days=1)

    date_count = (end_date - start_date).days + 1

    if len(data.location) > date_count:
        return {"error": "여행지 수가 여행일수보다 많습니다."}

    # data.location 에 있는 도시들의 좌표를 기반으로 가장 가깝게 연결
    # city_with_coordinate 에서 해당 도시 좌표를 가져옴
    city_coordinates = []
    for address in data.location:
        do = address.split(" ")[0]
        city = address.split(" ")[-1]

        if city in city_with_coordinate_dict:
            city_coordinates.append(city_with_coordinate_dict[city])
        else:
            return {"error": f"{city} is not a valid city."}
    
    # 도시 좌표를 기반으로 여행시 가장 가까운 도시 순으로 정렬
    loc_list = [i.split(" ")[-1] for i in data.location]
    print(loc_list)
    loc_list = optimal_route_bruteforce(loc_list)

    # 각 도시별로 여행일수 공평하게 배분
    base = date_count // len(data.location)
    remainder = date_count % len(data.location)
    days = [base + 1 if i < remainder else base for i in range(len(data.location))]

    es = ElasticSearch(start_date)
    es.connect_es()

    # 취향 세팅
    es.set_query("accommodation", data.taste.accommodation_taste)
    es.set_query("restaurant", data.taste.restaurant_taste)
    es.set_query("destination", data.taste.destination_taste)

    destinations = []

    now_coordinate = (loc_list[0][1], loc_list[0][2])  # 첫 번째 도시의 좌표

    days_index = 0
    days_count = 0

    for i in range(date_count):
        nodes = []
        days_count += 1

        # 지역 설정
        es.set_region(data.location[days_index])

        # 아침식사
        breakfast = es.restaurant_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (breakfast["lat"], breakfast["lon"])
        nodes.append(
            {
                "destination_type": "elastic_restaurant",
                "destination_id": breakfast["id"],
                "memo": ""
            }
        )

        # 관광지
        destination = es.destination_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (destination["lat"], destination["lon"])
        nodes.append(
            {
                "destination_type": "elastic_destination",
                "destination_id": destination["id"],
                "memo": ""
            }
        )

        # 점심식사
        lunch = es.restaurant_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (lunch["lat"], lunch["lon"])
        nodes.append(
            {
                "destination_type": "elastic_restaurant",
                "destination_id": lunch["id"],
                "memo": ""
            }
        )

        # 관광지
        destination = es.destination_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (destination["lat"], destination["lon"])
        nodes.append(
            {
                "destination_type": "elastic_destination",
                "destination_id": destination["id"],
                "memo": ""
            }
        )

        # 저녁식사
        dinner = es.restaurant_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (dinner["lat"], dinner["lon"])
        nodes.append(
            {
                "destination_type": "elastic_restaurant",
                "destination_id": dinner["id"],
                "memo": ""
            }
        )

        # 관광지
        destination = es.destination_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (destination["lat"], destination["lon"])
        nodes.append(
            {
                "destination_type": "elastic_destination",
                "destination_id": destination["id"],
                "memo": ""
            }
        )

        # 숙소
        accommodation = es.accommodation_search(now_coordinate[0], now_coordinate[1])
        now_coordinate = (accommodation["lat"], accommodation["lon"])
        nodes.append(
            {
                "destination_type": "elastic_accommodation",
                "destination_id": accommodation["id"],
                "memo": ""
            }
        )

        # 다음날로 넘기기
        es.next_day()

        destinations.append(
            {
                "location": data.location[days_index],
                "date": date_list[i],
                "nodes": nodes,
            }
        )

        if days_count >= days[days_index]:
            days_count = 0
            days_index += 1
            
            if days_index >= len(days):
                break
    
    es.disconnect_es()
    return destinations