from product_db import ProductDB

_product_db = None

def set_product_db(db_instance: ProductDB):
    global _product_db
    _product_db = db_instance

def get_product_db() -> ProductDB:
    return _product_db
