# trading/admin.py
from django.contrib import admin
from .models import Stock

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'name', 'buy_price', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'ticker')