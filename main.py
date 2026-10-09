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

    def find_transfer_routes(
        self,
        start: Stop,
        end: Stop,
        min_transfer: int = 5,
        is_weekend: bool = False,
    ) -> List[dict]:
        results = []
        active_trips = [t for t in self.trips if t.is_weekend == is_weekend]

        for trip1 in active_trips:
            dep_1 = trip1.arrival_at_stop(start)
            if dep_1 is None:
                continue

            start_idx = trip1.route.get_stop_index(start)
            next_stops = trip1.route.stops[start_idx + 1 :]

            for transfer_stop in next_stops:
                arr_1 = trip1.arrival_at_stop(transfer_stop)

                for trip2 in active_trips:
                    if trip1 == trip2:
                        continue

                    dep_2 = trip2.arrival_at_stop(transfer_stop)
                    arr_2 = trip2.arrival_at_stop(end)

                    if (
                        dep_2 is not None
                        and arr_2 is not None
                        and dep_2 < arr_2
                    ):
                        wait = dep_2 - arr_1
                        if wait >= min_transfer:
                            results.append(
                                {
                                    "trip1_route": trip1.route.number,
                                    "trip1_dep": time_to_str(dep_1),
                                    "transfer_stop": transfer_stop.name,
                                    "wait_min": wait,
                                    "trip2_route": trip2.route.number,
                                    "trip2_dep": time_to_str(dep_2),
                                    "final_arr": time_to_str(arr_2),
                                    "total_duration_min": arr_2 - dep_1,
                                }
                            )

        return sorted(results, key=lambda x: x["total_duration_min"])


def load_from_json(filename: str = "data.json") -> TransportSystem:
    system = TransportSystem()
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    for s_name in data["stops"]:
        system.add_stop(s_name)

    for r_data in data["routes"]:
        t_type = TransportType[r_data["transport_type"]]
        r_stops = [system.stops[name] for name in r_data["stops"]]
        route = Route(
            r_data["number"], t_type, r_stops, r_data["travel_times"]
        )
        system.add_route(route)

    for t_data in data["trips"]:
        route = system.routes[t_data["route_number"]]
        trip = Trip(
            route, t_data["departure"], t_data.get("is_weekend", False)
        )
        system.add_trip(trip)

    return system


def input_from_keyboard() -> TransportSystem:
    system = TransportSystem()
    print("\n--- Ручной ввод данных сети ---")
    n_stops = int(input("Количество остановок в сети: "))
    for i in range(n_stops):
        name = input(f"  Название остановки #{i + 1}: ").strip()
        system.add_stop(name)

    n_routes = int(input("\nКоличество маршрутов: "))
    for i in range(n_routes):
        print(f"\n--- Маршрут #{i + 1} ---")
        num = input("Номер маршрута: ").strip()
        type_str = input("Тип (BUS / TROLLEYBUS / BUS2): ").strip().upper()
        t_type = TransportType[type_str]

        stops_count = int(input("Количество остановок на этом маршруте: "))
        route_stops = []
        for s_i in range(stops_count):
            s_name = input(f"  Остановка #{s_i + 1}: ").strip()
            if s_name not in system.stops:
                system.add_stop(s_name)
            route_stops.append(system.stops[s_name])

        times = []
        for s_i in range(stops_count - 1):
            t = int(input(f"  Время хода между '{route_stops[s_i]}' и '{route_stops[s_i+1]}' (мин): "))
            times.append(t)

        route = Route(num, t_type, route_stops, times)
        system.add_route(route)

    n_trips = int(input("\nКоличество рейсов: "))
    for i in range(n_trips):
        print(f"--- Рейс #{i + 1} ---")
        r_num = input("Маршрут для рейса: ").strip()
        dep = input("Время отправления (ЧЧ:ММ): ").strip()
        is_wk = input("Рейс выходного дня? (y/n): ").strip().lower() == "y"
        system.add_trip(Trip(system.routes[r_num], dep, is_weekend=is_wk))

    return system


def main():
    print("=" * 60)
    print(" МОДЕЛЬ МАРШРУТОВ ГОРОДСКОГО ТРАНСПОРТА (ВОРОНЕЖ)")
    print("=" * 60)

    print("Выберите способ загрузки данных:")
    print("1. Загрузить из файла data.json")
    print("2. Ввести данные вручную с клавиатуры")
    choice = input("Ваш выбор (1 или 2, по умолчанию 1): ").strip()

    if choice == "2":
        system = input_from_keyboard()
    else:
        system = load_from_json("data.json")
        print("Данные успешно загружены из data.json!")

    while True:
        print("\n" + "=" * 45)
        print("ОСНОВНОЕ МЕНЮ:")
        print("1. Расписание по остановке")
        print("2. Расчёт прибытия на k-ю остановку")
        print("3. Расчёт интервалов движения")
        print("4. Поиск поездки (прямой путь или с 1 пересадкой)")
        print("0. Выход")
        cmd = input("Выберите действие: ").strip()

        if cmd == "0":
            print("Работа программы завершена.")
            break
        elif cmd == "1":
            print("Остановки:", list(system.stops.keys()))
            name = input("Название остановки: ").strip()
            if name in system.stops:
                is_wk = input("Выходной день? (y/n): ").strip().lower() == "y"
                for arr_t, r_num, t_type in system.get_schedule_for_stop(system.stops[name], is_wk):
                    print(f"  {arr_t} | {r_num} ({t_type})")
        elif cmd == "2":
            print("Маршруты:", list(system.routes.keys()))
            r_num = input("Номер маршрута: ").strip()
            if r_num in system.routes:
                r = system.routes[r_num]
                k = int(input(f"Номер остановки k (1..{len(r.stops)}): "))
                dep = input("Отправление (ЧЧ:ММ): ").strip()
                print(f"Прибытие: {time_to_str(Trip(r, dep).arrival_at_kth_stop(k))}")
        elif cmd == "3":
            print("Маршруты:", list(system.routes.keys()))
            r_num = input("Номер маршрута: ").strip()
            if r_num in system.routes:
                is_wk = input("Выходной день? (y/n): ").strip().lower() == "y"
                print(f"Интервалы (в мин): {system.calculate_headway(system.routes[r_num], is_wk)}")
        elif cmd == "4":
            print("Остановки:", list(system.stops.keys()))
            s_from = input("Откуда: ").strip()
            s_to = input("Куда: ").strip()
            if s_from in system.stops and s_to in system.stops:
                is_wk = input("Выходной день? (y/n): ").strip().lower() == "y"
                direct = system.find_direct_routes(system.stops[s_from], system.stops[s_to], is_wk)
                if direct:
                    print("[Прямой рейс]:", direct[0])
                else:
                    transfers = system.find_transfer_routes(system.stops[s_from], system.stops[s_to], 5, is_wk)
                    if transfers:
                        print("[С пересадкой]:", transfers[0])
                    else:
                        print("Маршрутов не найдено.")


if __name__ == "__main__":
    main()
