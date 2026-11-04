"""Print the public schema offline; never inspect user inputs or run services."""

import json

from api.main import app


if __name__ == "__main__":
    print(json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True))
