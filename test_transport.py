import unittest
from main import (
    TransportType,
    Stop,
    Route,
    Trip,
    TransportSystem,
    time_to_str,
    str_to_time,
)

class TestCityTransport(unittest.TestCase):
    def setUp(self):
        self.stop_station = Stop("Вокзал Воронеж-1")
        self.stop_lenina = Stop("Площадь Ленина")
        self.stop_vsu = Stop("ВГУ")
        self.stop_slava = Stop("Памятник Славы")

        self.route1 = Route(
            "Автобус 9КА",
            TransportType.BUS,
            [self.stop_station, self.stop_lenina, self.stop_vsu],
            [15, 5],
        )
        self.route2 = Route(
            "Троллейбус 7",
            TransportType.TROLLEYBUS,
            [self.stop_lenina, self.stop_slava],
            [20],
        )

        self.system = TransportSystem()
        self.system.add_route(self.route1)
        self.system.add_route(self.route2)

    def test_01_str_to_time(self):
        self.assertEqual(str_to_time("08:30"), 510)
        self.assertEqual(str_to_time("00:00"), 0)

    def test_02_time_to_str(self):
        self.assertEqual(time_to_str(510), "08:30")
        self.assertEqual(time_to_str(1439), "23:59")

    def test_03_transport_type_properties(self):
        self.assertEqual(TransportType.BUS.speed, 24)
        self.assertEqual(TransportType.BUS.places, 85)
        self.assertEqual(TransportType.TROLLEYBUS.places, 95)
        self.assertEqual(TransportType.BUS2.places, 40)

    def test_04_route_invalid_travel_times(self):
        with self.assertRaises(ValueError):
            Route("Err", TransportType.BUS, [self.stop_station, self.stop_lenina], [5, 10])

    def test_05_route_too_few_stops(self):
        with self.assertRaises(ValueError):
            Route("Err", TransportType.BUS, [self.stop_station], [])

    def test_06_time_to_kth_stop(self):
        self.assertEqual(self.route1.time_to_kth_stop(1), 0)
        self.assertEqual(self.route1.time_to_kth_stop(2), 15)
        self.assertEqual(self.route1.time_to_kth_stop(3), 20)

    def test_07_time_to_invalid_k(self):
        with self.assertRaises(IndexError):
            self.route1.time_to_kth_stop(0)
        with self.assertRaises(IndexError):
            self.route1.time_to_kth_stop(4)

    def test_08_trip_arrival_at_kth_stop(self):
        trip = Trip(self.route1, "08:00")
        self.assertEqual(trip.arrival_at_kth_stop(3), 500)

    def test_09_trip_arrival_at_stop(self):
        trip = Trip(self.route1, "10:00")
        self.assertEqual(
            trip.arrival_at_stop(self.stop_lenina), str_to_time("10:15")
        )
        self.assertIsNone(trip.arrival_at_stop(self.stop_slava))

    def test_10_schedule_weekday(self):
        self.system.add_trip(Trip(self.route1, "08:00", is_weekend=False))
        self.system.add_trip(Trip(self.route1, "08:30", is_weekend=False))
        sched = self.system.get_schedule_for_stop(
            self.stop_lenina, is_weekend=False
        )
        self.assertEqual(len(sched), 2)
        self.assertEqual(sched[0][0], "08:15")
        self.assertEqual(sched[1][0], "08:45")

    def test_11_schedule_weekend_separation(self):
        self.system.add_trip(Trip(self.route1, "08:00", is_weekend=False))
        self.system.add_trip(Trip(self.route1, "09:00", is_weekend=True))

        wk_sched = self.system.get_schedule_for_stop(
            self.stop_station, is_weekend=True
        )
        bd_sched = self.system.get_schedule_for_stop(
            self.stop_station, is_weekend=False
        )
        self.assertEqual(len(wk_sched), 1)
        self.assertEqual(wk_sched[0][0], "09:00")
        self.assertEqual(len(bd_sched), 1)
        self.assertEqual(bd_sched[0][0], "08:00")

    def test_12_calculate_headway(self):
        self.system.add_trip(Trip(self.route1, "08:00"))
        self.system.add_trip(Trip(self.route1, "08:15"))
        self.system.add_trip(Trip(self.route1, "08:35"))
        intervals = self.system.calculate_headway(
            self.route1, is_weekend=False
        )
        self.assertEqual(intervals, [15, 20])

    def test_13_direct_route_found(self):
        self.system.add_trip(Trip(self.route1, "08:00"))
        direct = self.system.find_direct_routes(
            self.stop_station, self.stop_vsu
        )
        self.assertEqual(len(direct), 1)
        self.assertEqual(direct[0]["duration_min"], 20)
        self.assertEqual(direct[0]["departure"], "08:00")
        self.assertEqual(direct[0]["arrival"], "08:20")

    def test_14_direct_route_none(self):
        self.system.add_trip(Trip(self.route1, "08:00"))
        direct = self.system.find_direct_routes(
            self.stop_vsu, self.stop_station
        )
        self.assertEqual(len(direct), 0)

    def test_15_transfer_route_success(self):
        self.system.add_trip(Trip(self.route1, "08:00"))
        self.system.add_trip(Trip(self.route2, "08:25"))

        transfers = self.system.find_transfer_routes(
            self.stop_station, self.stop_slava, min_transfer=5
        )
        self.assertEqual(len(transfers), 1)
        best = transfers[0]
        self.assertEqual(best["transfer_stop"], "Площадь Ленина")
        self.assertEqual(best["wait_min"], 10)
        self.assertEqual(best["total_duration_min"], 45)

    def test_16_transfer_route_insufficient_time(self):
        self.system.add_trip(Trip(self.route1, "08:00"))
        self.system.add_trip(Trip(self.route2, "08:18"))

        transfers = self.system.find_transfer_routes(
            self.stop_station, self.stop_slava, min_transfer=5
        )
        self.assertEqual(len(transfers), 0)

if __name__ == "__main__":
    unittest.main()
