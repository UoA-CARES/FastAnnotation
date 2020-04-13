class DtoStore:
    def __init__(self):
        self.dto_dict = {}

    def add_dto(self, model):
        self.dto_dict[model.name] = model

    def get_dtos(self):
        return self.dto_dict

    def get_dto(self, name):
        return self.dto_dict[name]