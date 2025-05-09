import math
import itertools
from typing import Tuple

from server.utils.city import city_with_coordinate_dict

# 두 지점 간 거리 계산 (Haversine 공식)
def haversine(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371  # 지구 반경 (km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def total_distance(route, locations):
    distance = 0
    for i in range(len(route) - 1):
        distance += haversine(locations[route[i]][1:], locations[route[i+1]][1:])
    return distance

def optimal_route_bruteforce(locations: list) -> list:
    locations = [(loc, city_with_coordinate_dict[loc]["lat"], city_with_coordinate_dict[loc]["lon"]) for loc in locations]  # (도시명, 위도, 경도)

    indices = list(range(len(locations)))
    min_route = None
    min_dist = float('inf')
    for perm in itertools.permutations(indices):
        dist = total_distance(perm, locations)
        if dist < min_dist:
            min_dist = dist
            min_route = perm
    return [locations[i] for i in min_route]