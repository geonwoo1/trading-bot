from django.db import models

class Stock(models.Model):
    ticker = models.CharField(max_length=10, verbose_name="종목코드")
    name = models.CharField(max_length=50, verbose_name="종목명")
    buy_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="매수가")
    is_active = models.BooleanField(default=True, verbose_name="보유중")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="매수일")

    def __str__(self):
        return f"{self.name} ({self.ticker})"
# Create your models here.
