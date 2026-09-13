"""内部SQLの対象IDをパラメータ化する。所有者条件とは常に併用する。"""
def id_scope(column, ids):
    if ids is None:
        return '', ()
    values = tuple(dict.fromkeys(ids))
    if any(type(value) is not int for value in values):
        raise ValueError('対象IDは整数で指定してください。')
    if not values:
        return ' AND 1 = 0', ()
    return f" AND {column} IN ({','.join('?' for _ in values)})", values
