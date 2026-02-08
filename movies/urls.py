from django.urls import path
from . import views

urlpatterns = [
    # Main Pages
    path('', views.home_view, name='home'),
    path('movies/', views.movies_list_view, name='movies'),
    path('movie/<int:movie_id>/', views.movie_detail_view, name='movie_detail'),

    # Authentication
    path('login-register/', views.login_register_view, name='login_register'),
    path('logout/', views.logout_view, name='logout'),

    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # path('dashboard/', views.dashboard_view, name='dashboard'),

    # Booking Process
    path('movie/<int:movie_id>/seats/', views.seat_selection_view, name='seat_selection'),
    path('checkout/', views.checkout_view, name='checkout'),
    
    # Admin Paths
    # path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('register-staff/', views.register_staff_view, name='register_staff'),
    path('add-show/', views.add_shows_view, name='add_shows'),
    path('staff/list-shows/', views.list_shows_view, name='list_shows'),
    
    path('api/chat/', views.chat_api, name='api_chat'),
    path('ticket/', views.ticket_view, name='ticket'),

    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('api/show/<int:show_id>/booked_seats/', views.show_booked_seats, name='show_booked_seats'),

    path('theaters/', views.theaters_list_view, name='theaters'), 

]

