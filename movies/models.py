# movies/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

UserModel = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(UserModel, on_delete=models.CASCADE)
    mobile_no = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=UserModel)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=UserModel)
def save_user_profile(sender, instance, **kwargs):
    # ensures profile exists and is saved if present
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Movie(models.Model):
    title = models.CharField(max_length=200)
    poster_url = models.URLField(max_length=500, help_text="URL of the movie poster")
    detail_poster_url = models.URLField(max_length=500, blank=True, null=True)
    genre = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    release_date = models.DateField()
    duration_minutes = models.IntegerField()
    votes = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    synopsis = models.TextField(blank=True)
    trailer_video_id = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2, default=0.00, help_text="Default price if show price missing")

    def __str__(self):
        return self.title

    def duration_formatted(self):
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return f"{hours}h {minutes}m"

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    show_date = models.DateField()
    show_time = models.TimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    hall = models.CharField(max_length=100, blank=True)
    seats_total = models.PositiveIntegerField(default=100)
    seats_booked = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    booked_seats = models.TextField(blank=True, default='') 

    class Meta:
        ordering = ['show_date', 'show_time']

    def __str__(self):
        return f"{self.movie.title} — {self.show_date} {self.show_time}"

class Booking(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='bookings')
    movie = models.ForeignKey(Movie, on_delete=models.SET_NULL, null=True, blank=True)
    show = models.ForeignKey(Show, on_delete=models.SET_NULL, null=True, blank=True)
    seats = models.CharField(max_length=500, help_text="Comma separated seat ids (e.g., A1,A2)")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_time = models.DateTimeField(auto_now_add=True)
    ticket_number = models.CharField(max_length=64, unique=True)

    def __str__(self):
        movie_title = self.movie.title if self.movie else "Unknown Movie"
        username = self.user.username if self.user else "Unknown User"
        return f"Booking {self.ticket_number} - {username} ({movie_title})"
