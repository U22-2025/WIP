import unittest
from unittest import mock
from common.clients.query_client import QueryClient

class TestPacketIDGeneratorIsolation(unittest.TestCase):
    def test_generators_are_independent_per_client(self):
        # それぞれのクライアントが独立したPacketIDGeneratorを持つことを確認
        with mock.patch('common.clients.utils.packet_id_generator.random.randint', side_effect=[0, 0]):
            client1 = QueryClient(debug=False)
            client2 = QueryClient(debug=False)

        first_id_client1 = client1.pid_generator.next_id()
        second_id_client1 = client1.pid_generator.next_id()
        first_id_client2 = client2.pid_generator.next_id()

        # クライアント1のジェネレーターが進んでもクライアント2には影響しない
        self.assertEqual(first_id_client1, 0)
        self.assertEqual(second_id_client1, 1)
        self.assertEqual(first_id_client2, 0)

if __name__ == '__main__':
    unittest.main()
