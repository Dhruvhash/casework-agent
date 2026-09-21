import unittest

from scripts.ingest.load_tigergraph import assert_clean, vertex


class LoadingStatisticsTests(unittest.TestCase):
    def response(self, file_level, object_level):
        return {"results": [{"statistics": {"parsingStatistics": {
            "fileLevel": file_level, "objectLevel": object_level,
        }}}]}

    def test_savanna_nested_statistics(self):
        body = self.response({"validLine": 2}, {
            "vertex": [{"typeName": "HHG_Customer", "validObject": 2}], "edge": [],
        })
        self.assertEqual(assert_clean(body, 2, [vertex("HHG_Customer", "customer_id")]), {"HHG_Customer": 2})

    def test_http_success_with_rejected_record_is_failure(self):
        body = self.response({"validLine": 1, "rejectLine": 1}, {
            "vertex": [{"typeName": "HHG_Customer", "validObject": 1}],
        })
        with self.assertRaisesRegex(RuntimeError, "rejected"):
            assert_clean(body, 2, [vertex("HHG_Customer", "customer_id")])

    def test_attribute_error_is_failure_even_when_line_count_matches(self):
        body = self.response({"validLine": 2}, {
            "vertex": [{"typeName": "HHG_Customer", "validObject": 2, "invalidAttribute": 1}],
        })
        with self.assertRaisesRegex(RuntimeError, "Invalid"):
            assert_clean(body, 2, [vertex("HHG_Customer", "customer_id")])


if __name__ == "__main__":
    unittest.main()
