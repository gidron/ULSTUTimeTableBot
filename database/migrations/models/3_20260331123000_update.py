from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "notify_by_change" BOOL NOT NULL DEFAULT True;

        DROP TABLE IF EXISTS "notification_settings";
        DROP TABLE IF EXISTS "notificationsettings";

        CREATE TABLE IF NOT EXISTS "schedulesnapshot" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_name" VARCHAR(32) NOT NULL UNIQUE,
    "week_number" INT NOT NULL,
    "payload_hash" VARCHAR(64) NOT NULL,
    "payload" JSONB NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

        CREATE TABLE IF NOT EXISTS "schedulechangedigest" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "group_name" VARCHAR(32) NOT NULL,
    "digest" VARCHAR(64) NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "schedulechangedigest";
        DROP TABLE IF EXISTS "schedulesnapshot";
        ALTER TABLE "user" DROP COLUMN IF EXISTS "notify_by_change";"""


MODELS_STATE = (
    "eJztl21v2jAQx78KyqtOKlVioDy8g7bTOrUgde00qaoik5hg4dhp7HRFFd+9tpOQBwKCTp"
    "Sh7V3yv7v47qezfXkzfOYiws8eOAqNXu3NoNBH8qGgn9YMGASZqgQBx0Q7RqnHmIsQOkJq"
    "E0g4kpKLuBPiQGBGpUojQpTIHOmIqZdJEcXPEbIF85CY6jwen6SMqYteEU9fg5k9wYi4hT"
    "Sxq9bWui3mgdauqfiqHdVqY9thJPJp5hzMxZTRpTemQqkeoiiEAqnPizBS6avskirTiuJM"
    "M5c4xVyMiyYwIiJX7pYMHEYVP5kN1wV6apU6sJrtZqdx3uxIF53JUmkv4vKy2uNATWB4by"
    "y0HQoYe2iMGTfh2VXoLqYwrGa3DCjhk0mX8aWwDsrPh682QdQTU/lqmRtg/ezfXXzr351Y"
    "5hdVCZNNHHf2MLEAbVI8M36q6/XzDgjzMR+imDBaQkxdMorZztsHxgbYAmMDrMWoTEWMuy"
    "L8I3wrTfjZ/CzQ3aYPQXd9IypbESHmtjx18UsFxwFjBEG65jDMx5V4jmXgvoAuN/qHgG7g"
    "NxiNblTSPufPRAvX9yWOD7eDKwlY45VOWKD8aVlk6vqYfgBpGvaJRHe9bg+ClEAubBfObU"
    "YJphXNeimpVGOtCC3RldccEthHZ+phX5gNYILzutmom52a1e21rJ7VPrMsAMymsRf6l/37"
    "qxJFL2RRYO96ahaj/uGrR42Rk1luIFLCGDqz3zB07RULA2yd76rJB35ZgRR6mo2qUOWfDN"
    "V9FGJnalSM24ll48ANM5//I/cRjdwvKOQqpR02bi7kOCce0GptsW+l19qNq23FQ1BtjR0g"
    "Ju7HCdAyt/t12fTvsvLzIlcUKN6DRYjff4yG1RBzISWQD1QW+OhiR5zWCObi6e/EuoGiqr"
    "ow5aTwTm77v8pcL25GA02BceGF+iv6A4NDXy+LdxwlqtM="
)
