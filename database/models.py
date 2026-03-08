from datetime import datetime
from tortoise import models, fields


class User(models.Model):
    tg_id = fields.CharField(max_length=10, unique=True)
    username = fields.CharField(max_length=32, null=True)
    name = fields.CharField(max_length=129)  # 128 max chars + spacebar
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_day_online = fields.DateField(default=datetime.today())
    group_name = fields.CharField(max_length=32, null=True)

    def __str__(self):
        return f"{self.name} - {self.username} - {self.tg_id}"
