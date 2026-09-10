import unittest
from unittest.mock import Mock, patch
import psycopg
from database import postgres


class DisconnectTest(unittest.TestCase):
    def connection(self):
        c = postgres.PostgresConnection.__new__(postgres.PostgresConnection)
        c.raw = Mock(closed=False)
        c.pool = Mock()
        c.closed = False
        c.ready = True
        return c

    def test_failed_cleanup_returns_broken_connection_once(self):
        c = self.connection()
        c.raw.rollback.side_effect = psycopg.OperationalError('lost connection')
        c.close()
        c.close()
        c.raw.close.assert_called_once()
        c.pool.putconn.assert_called_once_with(c.raw)
        self.assertTrue(c.closed)

    def test_already_closed_connection_is_returned_without_rollback(self):
        c = self.connection()
        c.raw.closed = True
        c.close()
        c.raw.rollback.assert_not_called()
        c.pool.putconn.assert_called_once_with(c.raw)

    def test_original_error_survives_cleanup_failure(self):
        c = self.connection()
        c.raw.rollback.side_effect = psycopg.OperationalError('cleanup error')
        with self.assertRaisesRegex(ValueError, 'original'):
            try:
                raise ValueError('original')
            finally:
                c.close()

    def test_write_failure_is_not_replayed(self):
        c = self.connection()
        c.raw.execute.side_effect = psycopg.OperationalError('uncertain write')
        with self.assertRaises(psycopg.OperationalError):
            c.execute('UPDATE users SET display_name=? WHERE id=?', ('test', 1))
        c.raw.execute.assert_called_once()

    def test_pool_checks_connections_on_checkout(self):
        postgres._pool.cache_clear()
        with patch.object(postgres, 'ConnectionPool') as pool:
            postgres._pool('unused-test-url')
            self.assertIs(pool.call_args.kwargs['check'], pool.check_connection)
        postgres._pool.cache_clear()
