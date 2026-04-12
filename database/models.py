from datetime import datetime

from tortoise import fields, models


class User(models.Model):
    tg_id = fields.CharField(max_length=10, unique=True)
    username = fields.CharField(max_length=32, null=True)
    name = fields.CharField(max_length=129)  # 128 max chars + spacebar
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    notify_by_change = fields.BooleanField(default=True)
    last_day_online = fields.DateField(default=datetime.today())
    group_name = fields.CharField(max_length=32, null=True)
    schedule_layout = fields.CharField(max_length=16, default="horizontal")

    def __str__(self):
        return f"{self.name} - {self.username} - {self.tg_id}"


class ScheduleSnapshot(models.Model):
    group_name = fields.CharField(max_length=32, unique=True)
    week_number = fields.IntField()
    payload_hash = fields.CharField(max_length=64)
    payload = fields.JSONField()
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return f"snapshot(group={self.group_name}, week={self.week_number})"


class ScheduleChangeDigest(models.Model):
    group_name = fields.CharField(max_length=32)
    digest = fields.CharField(max_length=64, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"change_digest(group={self.group_name}, digest={self.digest})"
