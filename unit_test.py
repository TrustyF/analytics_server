import unittest
from datetime import datetime
from app import app
from concurrent.futures import ThreadPoolExecutor, as_completed
import random


class BasicTests(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.test_event = {'uid': 3892445, 'name': 'page_nav', 'source': 'testing',
                           'type': 'nav', 'info': 'location',
                           'timestamp': datetime.now().timestamp() * 1000,
                           'geo': {'city': 'West End', 'country_code2': 'CA', 'country_code3': 'CAN',
                                   'country_flag': 'https://ipgeolocation.io/static/flags/ca_64.png',
                                   'country_name': 'Canada', 'state_prov': 'British Columbia', 'zipcode': 'V6Z'}}

    def tearDown(self):
        pass

    def test_spam_events(self):
        def send_test():
            rand = random.randint(0, 2)
            return self.client.post('/event/add', json=self.test_event)

        number_of_requests = 100
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(send_test): i for i in range(number_of_requests)}
            responses = []

            for future in as_completed(futures):
                response = future.result()
                responses.append(response)

        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
