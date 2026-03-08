from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "is_admin" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "user" ALTER COLUMN "username" TYPE VARCHAR(32) USING "username"::VARCHAR(32);
        ALTER TABLE "user" ALTER COLUMN "is_active" TYPE BOOL USING "is_active"::BOOL;
        ALTER TABLE "user" ALTER COLUMN "name" TYPE VARCHAR(129) USING "name"::VARCHAR(129);
        ALTER TABLE "user" ALTER COLUMN "last_day_online" SET DEFAULT '2026-03-08 19:32:50.486638';
        ALTER TABLE "user" ALTER COLUMN "last_day_online" TYPE DATE USING "last_day_online"::DATE;
        ALTER TABLE "user" ALTER COLUMN "tg_id" TYPE VARCHAR(10) USING "tg_id"::VARCHAR(10);
        ALTER TABLE "user" ALTER COLUMN "group_name" TYPE VARCHAR(32) USING "group_name"::VARCHAR(32);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "is_admin";
        ALTER TABLE "user" ALTER COLUMN "username" TYPE VARCHAR(32) USING "username"::VARCHAR(32);
        ALTER TABLE "user" ALTER COLUMN "is_active" TYPE BOOL USING "is_active"::BOOL;
        ALTER TABLE "user" ALTER COLUMN "name" TYPE VARCHAR(129) USING "name"::VARCHAR(129);
        ALTER TABLE "user" ALTER COLUMN "last_day_online" SET DEFAULT '2026-03-08 17:08:56.228084';
        ALTER TABLE "user" ALTER COLUMN "last_day_online" TYPE DATE USING "last_day_online"::DATE;
        ALTER TABLE "user" ALTER COLUMN "tg_id" TYPE VARCHAR(10) USING "tg_id"::VARCHAR(10);
        ALTER TABLE "user" ALTER COLUMN "group_name" TYPE VARCHAR(32) USING "group_name"::VARCHAR(32);"""


MODELS_STATE = (
    "eJztl21v2jAQx78KyqtOKlVIgALvgHZapxakDqZJVRWZxAQLx05jpyuq+O61HUIeCIiwUY"
    "a0d8n/7uK7n3z25V3zqAMxuxozGGidyrtGgAfFQ0a/rGjA9xNVChxMsHIMY48J4wGwudCm"
    "ADMoJAcyO0A+R5QIlYQYS5HawhERN5FCgl5CaHHqQj5TeTw9CxkRB75BFr/6c2uKIHYyaS"
    "JHrq10iy98pd0R/lU5ytUmlk1x6JHE2V/wGSVrb0S4VF1IYAA4lJ/nQSjTl9mtqowrijJN"
    "XKIUUzEOnIIQ81S5ezKwKZH8RDZMFejKVapGrX5db5nNeku4qEzWyvUyKi+pPQpUBAYjba"
    "nsgIPIQ2FMuHHXKkLXn4GgmN06IIdPJJ3HF8M6KT8PvFkYEpfPxGtN3wHrZ/ex/637eFHT"
    "v8hKqNjE0c4erCyGMkmeCT+569VzCYTpmIMorhitIcYuCcWk846B0TT2wGgaWzFKUxZjWY"
    "R/hG9jE342v5rR3mcfGu3tG1HasggRs8Spi14LOPYoxRCQLYdhOi7HcyICjwV03egHAd3B"
    "rzcc3sukPcZesBLuRjmO44ferQCs8AonxGH6tMwydTxEDkAah30i0bLX7UmQYsC45YCFRQ"
    "lGpGCz3ggqxVgLQnN0xTUHOfLglXw4FmbN0I1mVTereqtSa3dMo9PQr+qtZtNsaUehf9Md"
    "3eYougENfavsqZmNOs+z8+/cPXKOnM5TE5EUJsCe/waBY21YqEG3+W6aPMPLK4AAV7GRFc"
    "r8V1N1FwbInmkF8/bKsnPiBonP/5n7jGbuVxgwmVKJzk2FnGfbGo3GHn0rvLY2rrJlT0HZ"
    "GiUgrtzPE2BN3+/fZdfPy8bfi1iRw6gHsxC//xgOiiGmQnIgx0QU+OQgm19WMGL8+d/Euo"
    "OirDoz5sTwLh66v/Jc+/fDnqJAGXcD9RX1gd6pr5flB0koqzM="
)
