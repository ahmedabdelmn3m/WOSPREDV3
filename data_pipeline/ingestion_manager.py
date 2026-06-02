class IngestionManager:
    def __init__(self, validator, parser):
        self.validator = validator
        self.parser = parser

    def process_report(self, raw_data):
        if self.validator.validate(raw_data):
            return self.parser.parse(raw_data)
        return None
