"""Модель городского транспорта Воронежа (Python)."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import json


def time_to_str(minutes: int) -> str:
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def str_to_time(time_str: str) -> int:
    h, m = map(int, time_str.strip().split(":"))
    return h * 60 + m


class TransportType(Enum):
    BUS = ("Автобус", 24, 85)
    TROLLEYBUS = ("Троллейбус", 20, 95)
    BUS2 = ("Маршрутка", 28, 40)

    def __init__(self, title: str, speed: int, places: int):
        self.title = title
        self.speed = speed
        self.places = places


@dataclass(frozen=True)
class Stop:
    name: str

    def __repr__(self) -> str:
        return self.name


class Route:
    def __init__(
        self,
        number: str,
        transport_type: TransportType,
        stops: List[Stop],
        times: List[int],
    ):
        if len(stops) < 2:
            raise ValueError("Маршрут должен состоять минимум из двух остановок.")
        if len(times) != len(stops) - 1:
            raise ValueError("Количество интервалов хода должно быть на 1 меньше числа остановок.")

        self.number = number
        self.transport_type = transport_type
        self.stops = stops
        self.times = times

    def get_stop_index(self, stop: Stop) -> Optional[int]:
        return self.stops.index(stop) if stop in self.stops else None

    def time_to_kth_stop(self, k: int) -> int:
        if k < 1 or k > len(self.stops):
            raise IndexError("Некорректный номер остановки k.")
        return sum(self.times[: k - 1])

    def travel_time_between(self, start: Stop, end: Stop) -> Optional[int]:
        if start in self.stops and end in self.stops:
            idx1 = self.stops.index(start)
            idx2 = self.stops.index(end)
            if idx1 < idx2:
                return sum(self.times[idx1:idx2])
        return None


class Trip:
    def __init__(
        self, route: Route, departure_time: str, is_weekend: bool = False
    ):
        self.route = route
        self.dep_min = str_to_time(departure_time)
        self.is_weekend = is_weekend

    def arrival_at_kth_stop(self, k: int) -> int:
        return self.dep_min + self.route.time_to_kth_stop(k)

    def arrival_at_stop(self, stop: Stop) -> Optional[int]:
        idx = self.route.get_stop_index(stop)
        if idx is not None:
            return self.arrival_at_kth_stop(idx + 1)
        return None


class TransportSystem:
    def __init__(self):
        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: List[Trip] = []

    def add_stop(self, name: str) -> Stop:
        if name not in self.stops:
            self.stops[name] = Stop(name)
        return self.stops[name]

    def add_route(self, route: Route):
        self.routes[route.number] = route

    def add_trip(self, trip: Trip):
        self.trips.append(trip)

    def get_schedule_for_stop(
        self, stop: Stop, is_weekend: bool = False
    ) -> List[Tuple[str, str, str]]:
        schedule = []
        for trip in self.trips:
            if trip.is_weekend == is_weekend:
                arr = trip.arrival_at_stop(stop)
                if arr is not None:
                    schedule.append(
                        (
                            time_to_str(arr),
                            trip.route.number,
                            trip.route.transport_type.title,
                        )
                    )
        return sorted(schedule, key=lambda x: x[0])

    def calculate_headway(
        self, route: Route, is_weekend: bool = False
    ) -> List[int]:
        route_trips = [
            t
            for t in self.trips
            if t.route == route and t.is_weekend == is_weekend
        ]
        route_trips.sort(key=lambda t: t.dep_min)

        intervals = []
        for i in range(1, len(route_trips)):
            intervals.append(
                route_trips[i].dep_min - route_trips[i - 1].dep_min
            )
        return intervals

    def find_direct_routes(
        self, start: Stop, end: Stop, is_weekend: bool = False
    ) -> List[dict]:
        results = []
        for trip in self.trips:
            if trip.is_weekend != is_weekend:
                continue

            dep = trip.arrival_at_stop(start)
            arr = trip.arrival_at_stop(end)

            if dep is not None and arr is not None and dep < arr:
                results.append(
                    {
                        "route": trip.route.number,
                        "type": trip.route.transport_type.title,
                        "departure": time_to_str(dep),
                        "arrival": time_to_str(arr),
                        "duration_min": arr - dep,
                    }
                )
        return sorted(results, key=lambda x: x["duration_min"])
