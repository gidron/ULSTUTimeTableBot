from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tg_id" VARCHAR(10) NOT NULL UNIQUE,
    "username" VARCHAR(32),
    "name" VARCHAR(129) NOT NULL,
    "is_active" BOOL NOT NULL,
    "last_day_online" DATE NOT NULL,
    "group_name" VARCHAR(32) NOT NULL
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztl21v2jAQx78KyqtOGlUwD015B22ndWpBauk0aZosk5hg4dhp7HRFHd99tkPIAwHBNr"
    "oO7V3yv7v4/IvvcnmxAu5hKk4fBI6sbu3FYijA6qKgv69ZKAwzVQsSjalxjFOPsZARcqXS"
    "JogKrCQPCzcioSScKZXFlGqRu8qRMD+TYkYeYwwl97Gcmjy+flMyYR5+xiK9DWdwQjD1Cm"
    "kST69tdCjnodGumfxgHPVqY+hyGgcscw7ncsrZypswqVUfMxwhifXjZRTr9HV2y12mO0oy"
    "zVySFHMxHp6gmMrcdscw0ywIB8MRvL8aQWjtAcjlTMNVqQqze1+nUAeN1lnLaXZajnIxaa"
    "6Us0WydAYmCTR4BiNrYexIosTDMM6gSh9Wcb2Yoqga7CqgxFYlXWabkny7cAP0DClmvpyq"
    "24a9heTn3t3Fx97dScN+pxfk6vgnNTFYWoAxadgZXF0v5noPvvmYX0K8BLginLpkiLOafX"
    "XGTbAD4ybYyFibioz35ftbbNeO75uC2wDnu5xgcL75CGtbkS8RUHV68lQBuc85xYhtaMD5"
    "uBLssQo8FO20fxyA9ha4/eHwRj85EOKRGuF6VIL8cNu/UvQNe+VEJM536Aw4RUJCD80hZ5"
    "SwCuyXilg184rQEnn1HcCSBPhUXxzqFVjABp263azbTq1x1rWdbrtzCoBjOy3r9V/NZW90"
    "VULsRzwO4b6doxh1hP3jzzRnPb9NZrlhQwtj5M6+o8iDaxYO+CbfdVMAgrKCGPINOL1Dnf"
    "9ymu3hiLhTq2LOXVq2Troo8/k/6x7LrPuEI6FT2qPmcyFHWPCg3d6h4pXXxpI3tmJz1UW1"
    "B+Gl+xHSbdi7/VBs+6NY+6VQK0qclHaR8Kf74aCacC6kPA0QV9Z+1CgRa73iH6C9Ba6GUR"
    "jHUqYnt70vZdwXN8O+gcOF9CPzFPOA/t/+mC1+Aiwin20="
)
