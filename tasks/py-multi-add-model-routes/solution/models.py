class User:
    _users = []
    _next_id = 1

    def __init__(self, name: str, email: str):
        self.id = User._next_id
        User._next_id += 1
        self.name = name
        self.email = email
        User._users.append(self)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email}

    @classmethod
    def all(cls):
        return [u.to_dict() for u in cls._users]

    @classmethod
    def reset(cls):
        cls._users.clear()
        cls._next_id = 1


class Product:
    _products = []
    _next_id = 1

    def __init__(self, name: str, price: float):
        self.id = Product._next_id
        Product._next_id += 1
        self.name = name
        self.price = price
        Product._products.append(self)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "price": self.price}

    @classmethod
    def all(cls):
        return [p.to_dict() for p in cls._products]

    @classmethod
    def reset(cls):
        cls._products.clear()
        cls._next_id = 1
