from django.core.management.base import BaseCommand
from movies.models import Booking

class Command(BaseCommand):
    help = "Fix Booking.total_price when it's zero or null, using show.price -> movie.price -> default"

    def handle(self, *args, **options):
        fixed = 0
        qs = Booking.objects.filter(total_price__in=[0, 0.0, None])
        for b in qs:
            seats_count = len([s for s in (b.seats or '').split(',') if s.strip()])

            # prefer show.price -> movie.price -> fallback 50
            if b.show and getattr(b.show, 'price', None) is not None and float(b.show.price) > 0:
                price = float(b.show.price)
            elif b.movie and getattr(b.movie, 'price', None) is not None and float(b.movie.price) > 0:
                price = float(b.movie.price)
            else:
                price = 50.0   # DEFAULT PRICE NOW = 50

            b.total_price = price * max(1, seats_count)
            b.save(update_fields=['total_price'])
            fixed += 1

        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed} bookings"))
