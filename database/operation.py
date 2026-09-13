"""1回のサービス操作内で接続・トランザクション・有効性確認を共有する。"""
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps


@dataclass
class Operation:
    connection: object = None
    checked_users: set = field(default_factory=set)
    failed: bool = False


_current_operation = ContextVar('metea_database_operation', default=None)


def current_operation():
    return _current_operation.get()


class BorrowedConnection:
    """Repositoryのcommit/closeは外側の操作完了まで保留する。"""
    def __init__(self, operation):
        self.operation = operation

    def __getattr__(self, name):
        return getattr(self.operation.connection, name)

    def commit(self):
        pass

    def rollback(self):
        self.operation.failed = True

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.rollback()
        return False


def database_operation(function):
    """読取も更新も操作の境界で終了し、例外時は一括で巻き戻す。"""
    @wraps(function)
    def wrapped(*args, **kwargs):
        active = current_operation()
        if active is not None:
            try:
                return function(*args, **kwargs)
            except BaseException:
                active.failed = True
                raise
        operation = Operation()
        token = _current_operation.set(operation)
        try:
            result = function(*args, **kwargs)
            if operation.failed:
                raise RuntimeError('保存処理を完了できませんでした。')
            if operation.connection is not None:
                operation.connection.commit()
            return result
        except BaseException:
            if operation.connection is not None:
                operation.connection.rollback()
            raise
        finally:
            _current_operation.reset(token)
            if operation.connection is not None:
                operation.connection.close()
    return wrapped
