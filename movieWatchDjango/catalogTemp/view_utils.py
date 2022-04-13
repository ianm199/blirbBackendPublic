from django.db import connection

def query_db(query: str, headings: list):
    """
    Allows you to query the database.
    :param query: query to make
    :param headings: list of str heading for the dictionaries returned. Corresponds to the name of individual rows
    :return: return list of dictionarys of results from query based on the query made and the headings
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    result = []
    for row in rows:
        row_dict = dict(zip(headings, row))
        result.append(row_dict)
    return result

def execute_query_nonatomic(query):
    """
    Exexcute non atomic query on db
    :param query: str sql query to exexcute
    :return: n/a performs insert/update/delete
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
