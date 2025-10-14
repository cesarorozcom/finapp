from database.base import engine

from database.models import concept_table, category_table, metadata_obj

from sqlalchemy import select, insert

metadata_obj.create_all(engine)


def execute_insert(**kwargs) -> list:
    with engine.connect() as conn:
        insert_stmt = insert(kwargs['table_name']).values(kwargs['values'])
        result = conn.execute(insert_stmt)
        return result.inserted_primary_key_rows


print(execute_insert(**dict(table_name=category_table,
                            values=[
                                {"name": "Hogar"},
                                {"name": "Ropa / Vestido"}
                            ])))
