# movies/admin.py
from django.contrib import admin
from .models import Profile, Movie, Show, Booking

admin.site.register(Profile)

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'rating', 'is_featured')
    list_filter = ('is_featured', 'genre', 'release_date')
    search_fields = ('title', 'synopsis')
    list_editable = ('is_featured',)

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ('movie', 'show_date', 'show_time', 'price', 'is_active', 'seats_booked', 'seats_total')
    list_filter = ('show_date', 'is_active')
    search_fields = ('movie__title',)
    raw_id_fields = ('movie',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'user', 'movie', 'show', 'total_price', 'booking_time')
    search_fields = ('ticket_number', 'user__username', 'movie__title')
    readonly_fields = ('booking_time',)
