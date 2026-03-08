from tortoise import Tortoise, run_async
from core.config import get_settings

settings = get_settings()

TORTOISE_ORM_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "database": settings.pg_database,
                "password": settings.pg_password,
                "host": settings.pg_host,
                "port": settings.pg_port,
                "user": settings.pg_user,
            }
        }
    },
    "apps": {
        "models": {
            "models": ["database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


async def init_database(generate_schemas: bool = True):
    await Tortoise.init(TORTOISE_ORM_CONFIG)
    if generate_schemas:
        await Tortoise.generate_schemas()


if __name__ == "__main__":
    run_async(init_database())
