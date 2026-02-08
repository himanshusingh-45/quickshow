# movies/views.py
import os
import logging
import json
import uuid
from datetime import date, timedelta
import traceback
from django.db import IntegrityError
import traceback
import requests

from requests.exceptions import RequestException
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

from .models import Movie, Profile, Show, Booking
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    UserUpdateForm,
    ProfileUpdateForm
)

logger = logging.getLogger(__name__)

def _get_api_key():
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        # fallback to settings if present
        key = getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "OPENAI_API_KEY", None)
    if not key:
        return None
    return str(key).strip()

def _get_groq_base():
    
    raw = os.environ.get("GROQ_API_URL") or getattr(settings, "GROQ_API_URL", "") or ""
    raw = raw.strip()
    if not raw:
        return "https://api.groq.com"
    return raw.rstrip('/')

def _call_groq_chat(messages, model="gpt-4o-mini", max_tokens=600, timeout=15):
    
    key = _get_api_key()
    if not key:
        return {'error': 'Chat service not configured (missing API key).'}

    base = _get_groq_base()
    # if user already set a full openai path (contains /openai/), use it
    if "/openai/" in base.lower():
        endpoint = base
    else:
        endpoint = base + "/openai/v1/chat/completions"

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
    except RequestException:
        logger.exception("Network error calling Groq/OpenAI-compatible endpoint")
        return {'error': 'Upstream connection error.'}

    status = resp.status_code
    text_snippet = (resp.text or "")[:1000]
    logger.debug("Chat provider response: status=%s, snippet=%s", status, text_snippet)

    # Successful response
    if status == 200:
        try:
            data = resp.json()
        except Exception:
            return {'error': 'Invalid JSON from chat provider.'}
        # Try OpenAI shape first
        try:
            choices = data.get('choices') or []
            if choices:
                message = choices[0].get('message') or {}
                content = message.get('content') or message.get('text') or None
                if content:
                    return {'reply': content}
            if isinstance(data.get('result'), str):
                return {'reply': data.get('result')}
            return {'reply': json.dumps(data)}
        except Exception:
            return {'reply': json.dumps(data)}

    try:
        data = resp.json()
        err_msg = data.get('error', {}).get('message') or data.get('message') or str(data)
    except Exception:
        err_msg = resp.text or f"HTTP {status}"
    logger.warning("Chat provider returned %s: %s", status, err_msg)

    if status in (401, 403):
        return {'error': 'API key unauthorized.'}
    if status in (429, 402):
        return {'error': 'Quota exceeded or rate limited by provider.'}
    return {'error': f'Chat provider error: {err_msg}'}


@require_POST
@login_required
def chat_api(request):
    
    try:
        payload = json.loads(request.body.decode('utf-8'))
        user_message = payload.get('message', '').strip()
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Build messages in OpenAI chat format
    messages = [
        {"role": "system", "content": "You are TicketAdda assistant. Help users with showtimes, bookings and site help."},
        {"role": "user", "content": user_message},
    ]

    # Try calling the chat provider
    model_name = payload.get('model') or os.environ.get('GROQ_MODEL') or "gpt-4o-mini"
    result = _call_groq_chat(messages=messages, model=model_name, max_tokens=600)

    if 'reply' in result:
        return JsonResponse({'reply': result['reply']})
    # Error: map to suitable status codes
    err = result.get('error') or 'Unknown error from chat provider.'
    lerr = err.lower()
    if 'unauthorized' in lerr or 'invalid' in lerr or 'api key' in lerr:
        status = 401
    elif 'quota' in lerr or 'rate' in lerr or 'limited' in lerr:
        status = 429
    elif 'connection' in lerr:
        status = 502
    else:
        status = 502
    logger.info("chat_api: returning error to frontend: %s", err)
    return JsonResponse({'error': err}, status=status)

# ---------------- site views (unchanged behavior) ----------------
def home_view(request):
    all_movies = Movie.objects.all().order_by('-release_date')
    return render(request, 'index.html', {'all_movies': all_movies})


def movies_list_view(request):
    """
    Movies listing view with optional search.
    Accepts `?search=...` and filters movies by title, genre or synopsis (case-insensitive).
    Returns 'all_movies' (QuerySet) and 'search_query' (string) to the template.
    """
    query = (request.GET.get('search') or '').strip()
    movies = Movie.objects.all().order_by('-release_date')

    if query:
        # search in title, genre and synopsis
        movies = movies.filter(
            Q(title__icontains=query) |
            Q(genre__icontains=query) |
            Q(synopsis__icontains=query)
        ).distinct()

    return render(request, 'movies.html', {
        'all_movies': movies,
        'search_query': query,
    })


def movie_detail_view(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    return render(request, 'movie_detail.html', {'movie': movie})

def login_register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    login_form = CustomAuthenticationForm()
    register_form = CustomUserCreationForm()

    if request.method == 'POST':
        if 'register' in request.POST:
            register_form = CustomUserCreationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save(commit=False)
                user.email = register_form.cleaned_data.get('email')
                user.save()
                mobile = register_form.cleaned_data.get('mobile_no')
                if hasattr(user, 'profile'):
                    user.profile.mobile_no = mobile or ''
                    user.profile.save()
                else:
                    Profile.objects.create(user=user, mobile_no=mobile or '')
                messages.success(request, 'Registration successful! Please log in.')
                return redirect('login_register')
        elif 'login' in request.POST:
            login_form = CustomAuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                login_user = login_form.get_user()
                from django.contrib.auth import login as auth_login
                auth_login(request, login_user)
                messages.success(request, f'Welcome back, {login_user.username}!')
                return redirect('home')

    return render(request, 'login_register.html', {
        'login_form': login_form,
        'register_form': register_form,
    })

def logout_view(request):
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profile updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'profile.html', {'u_form': u_form, 'p_form': p_form})

@login_required
def seat_selection_view(request, movie_id):
    """
    Render seat-selection and include initial_booked_seats (list) in context.
    Defaults to first upcoming show when show_id not provided so the template
    can render booked seats for the initially-active time slot.
    """
    movie = get_object_or_404(Movie, pk=movie_id)
    upcoming_shows = Show.objects.filter(movie=movie, is_active=True).order_by('show_date', 'show_time')

    # Determine which show to show booked seats for: show_id from GET or first upcoming
    show_id = request.GET.get('show_id')
    if not show_id and upcoming_shows.exists():
        show_id = str(upcoming_shows.first().id)

    initial_booked = []
    if show_id:
        try:
            s = Show.objects.filter(pk=int(show_id)).first()
        except Exception:
            s = None
        if s:
            # prefer a booked_seats text field if the model has it
            if hasattr(s, 'booked_seats') and (s.booked_seats or '').strip():
                initial_booked = [x.strip() for x in (s.booked_seats or '').split(',') if x.strip()]
            else:
                # fallback: collect from Booking rows
                rows = Booking.objects.filter(show=s).values_list('seats', flat=True)
                all_seats = []
                for r in rows:
                    if not r:
                        continue
                    parts = [p.strip() for p in r.split(',') if p.strip()]
                    all_seats.extend(parts)
                initial_booked = sorted(set(all_seats))

    return render(request, 'seat_selection.html', {
        'movie': movie,
        'upcoming_shows': upcoming_shows,
        'initial_booked_seats': initial_booked,
    })


@require_GET
@login_required
def show_booked_seats(request, show_id):
    try:
        show = Show.objects.filter(pk=int(show_id)).first()
    except Exception:
        show = None
    if not show:
        return JsonResponse({'booked': []})
    if hasattr(show, 'booked_seats') and (show.booked_seats or '').strip():
        booked = [s.strip() for s in (show.booked_seats or '').split(',') if s.strip()]
    else:
        rows = Booking.objects.filter(show=show).values_list('seats', flat=True)
        booked = []
        for r in rows:
            if not r:
                continue
            booked.extend([p.strip() for p in r.split(',') if p.strip()])
        booked = sorted(set(booked))
    return JsonResponse({'booked': booked})

@login_required
def checkout_view(request):
    if request.method == "GET":
        movie_id = request.GET.get('movie_id')
        show_id = request.GET.get('show_id')
        seats = request.GET.get('seats', '')
        time = request.GET.get('time', '')
        date_val = request.GET.get('date') or timezone.localdate()

        movie = Movie.objects.filter(pk=movie_id).first() if movie_id else None

        show = None
        try:
            if show_id and str(show_id).strip().lower() not in ('undefined','null',''):
               show_pk = int(str(show_id).strip())
               # normal fetch for GET
               show = Show.objects.filter(pk=show_pk).first()
        except Exception:
            show = None

        seat_list = [s.strip() for s in seats.split(',') if s.strip()]

        if show and getattr(show,'price',None):
            price_per_ticket = float(show.price)
        elif movie and getattr(movie,'price',None):
            price_per_ticket = float(movie.price)
        else:
            price_per_ticket = 50.0

        total_price = price_per_ticket * max(1, len(seat_list))

        return render(request, 'checkout.html', {
            'movie': movie,
            'show': show,
            'seats': seats,
            'seat_list': seat_list,
            'time': time,
            'date': date_val,
            'price_per_ticket': price_per_ticket,
            'total_price': total_price,
        })

    # POST: create booking (safe check for already-booked seats)
    elif request.method == "POST":
        show_id = request.POST.get('show_id')
        seats = request.POST.get('seats', '')
        movie_id = request.POST.get('movie_id') or request.POST.get('movie')
        seat_list = [s.strip() for s in seats.split(',') if s.strip()]

        movie = Movie.objects.filter(pk=movie_id).first() if movie_id else None
        show = None
        try:
            if show_id and str(show_id).strip().lower() not in ('undefined','null',''):
                show_pk = int(str(show_id).strip())
                show = Show.objects.filter(pk=show_pk).first()
        except Exception:
            show = None

        if show and getattr(show,'price',None):
            price_per_ticket = float(show.price)
        elif movie and getattr(movie,'price',None):
            price_per_ticket = float(movie.price)
        else:
            price_per_ticket = 50.0

        total_price = price_per_ticket * max(1, len(seat_list))
        ticket_no = uuid.uuid4().hex[:12].upper()

        # If we have a show, check & lock row inside transaction
        if show:
            try:
                with transaction.atomic():
                    # try locking show row (if DB supports it)
                    try:
                        locked_show = Show.objects.select_for_update().get(pk=show.pk)
                    except Exception:
                        locked_show = Show.objects.filter(pk=show.pk).first()

                    # build existing set (prefer booked_seats field)
                    existing = set()
                    if hasattr(locked_show, 'booked_seats') and (locked_show.booked_seats or '').strip():
                        existing = set([x.strip() for x in (locked_show.booked_seats or '').split(',') if x.strip()])
                    else:
                        rows = Booking.objects.filter(show=locked_show).values_list('seats', flat=True)
                        for r in rows:
                            if not r:
                                continue
                            existing.update([p.strip() for p in r.split(',') if p.strip()])

                    requested = set([s.strip() for s in seat_list if s.strip()])
                    conflicts = existing.intersection(requested)

                    if conflicts:
                        conflict_list = sorted(conflicts)
                        msg = f'Some seats already booked: {", ".join(conflict_list)}'
                        logger.info("Booking conflict for user=%s show=%s requested=%s existing=%s",
                                    request.user.username if request.user.is_authenticated else None,
                                    locked_show.pk, list(requested), list(existing))
                        # XHR -> return JSON with conflict list and 409
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({'success': False, 'error': msg, 'conflicts': conflict_list}, status=409)
                        # Non-XHR -> flash message and redirect back
                        messages.error(request, msg)
                        return redirect(request.META.get('HTTP_REFERER', '/'))

                    # No conflicts: update show and create booking atomically
                    combined = sorted(existing.union(requested))
                    if hasattr(locked_show, 'booked_seats'):
                        locked_show.booked_seats = ','.join(combined)
                        update_fields = ['booked_seats', 'seats_booked']
                    else:
                        update_fields = ['seats_booked']
                    locked_show.seats_booked = (locked_show.seats_booked or 0) + len(requested)
                    locked_show.save(update_fields=update_fields)

                    booking = Booking.objects.create(
                        user=request.user,
                        movie=movie,
                        show=locked_show,
                        seats=','.join(sorted(requested)),
                        total_price=total_price,
                        ticket_number=ticket_no
                    )
            except Exception as e:
                logger.exception("Error creating booking (show=%s user=%s seats=%s): %s", show.pk if show else None, request.user, seat_list, exc_info=True)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Booking failed due to server error.'}, status=500)
                messages.error(request, "Booking failed due to server error.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            # create booking without show lock
            try:
                booking = Booking.objects.create(
                    user=request.user,
                    movie=movie,
                    show=None,
                    seats=','.join(sorted(seat_list)),
                    total_price=total_price,
                    ticket_number=ticket_no
                )
            except Exception:
                logger.exception("Error creating booking (no-show) for user=%s seats=%s", request.user, seat_list, exc_info=True)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Booking failed.'}, status=500)
                messages.error(request, "Booking failed.")
                return redirect(request.META.get('HTTP_REFERER', '/'))

        # Success: redirect to ticket
        ticket_url = reverse('ticket') + f'?ticket={booking.ticket_number}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'ticket_number': booking.ticket_number, 'ticket_url': ticket_url})
        return redirect(ticket_url)


def ticket_view(request):
    ticket_no = request.GET.get('ticket') or request.GET.get('ticket_number')
    booking = Booking.objects.filter(ticket_number=ticket_no).select_related('movie','show','user').first() if ticket_no else None
    auto_print = request.GET.get('auto') == '1'
    return render(request, 'ticket.html', {'booking': booking, 'auto_print': auto_print})

@login_required
def my_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).select_related('movie','show').order_by('-booking_time')
    
    return render(request, 'my_bookings.html', {'bookings': bookings})

@login_required
def dashboard_view(request):
    my_bookings_count = Booking.objects.filter(user=request.user).count()
    return render(request, 'dashboard.html', {'my_bookings_count': my_bookings_count})


@staff_member_required
def admin_dashboard_view(request):
    total_users_count = User.objects.count()
    total_revenue = Movie.objects.aggregate(total=Sum('revenue'))['total'] or 0.0
    total_bookings_count = Booking.objects.count()
    active_shows = Show.objects.filter(is_active=True).select_related('movie').order_by('show_date','show_time')
    return render(request, 'dashboard.html', {
        'active_shows': active_shows,
        'active_shows_count': active_shows.count(),
        'total_users_count': total_users_count,
        'total_revenue': total_revenue,
        'total_bookings_count': total_bookings_count,
    })

@login_required
def dashboard(request):
    active_shows = Show.objects.filter(
        is_active=True
    ).select_related('movie').order_by('show_date', 'show_time')

    context = {
        # UI same for all
        "active_shows": active_shows,
        "active_shows_count": active_shows.count(),

        # numbers (safe to show read-only)
        "total_users_count": User.objects.count(),
        "total_bookings_count": Booking.objects.count(),
        "total_revenue": Movie.objects.aggregate(
            total=Sum('revenue')
        )['total'] or 0,

        # user info
        "my_bookings_count": Booking.objects.filter(
            user=request.user
        ).count(),

        # permission flag
        "is_admin": request.user.is_staff,
    }

    return render(request, "dashboard.html", context)



@user_passes_test(lambda u: u.is_superuser)
def register_staff_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get('email')
            user.is_staff = True
            user.save()
            Profile.objects.create(user=user)
            messages.success(request, "Staff created")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register_staff.html', {'form': form})

@staff_member_required
def add_shows_view(request):
    now_playing_movies = Movie.objects.filter(is_featured=True).order_by('-release_date')
    if request.method == 'POST':
        movie_id = request.POST.get('movie_id')
        price = request.POST.get('price')
        show_date = request.POST.get('show_date')
        show_time = request.POST.get('show_time')
        if not movie_id or not price or not show_date or not show_time:
            messages.error(request, "All fields are required.")
            return redirect('add_shows')
        movie = get_object_or_404(Movie, pk=movie_id)
        Show.objects.create(movie=movie, price=price, show_date=show_date, show_time=show_time)
        messages.success(request, "Show added")
        return redirect('add_shows')
    return render(request, 'add_shows.html', {'now_playing_movies': now_playing_movies})

@staff_member_required
def list_shows_view(request):
    movies = Movie.objects.order_by('-release_date')
    return render(request, 'list_shows.html', {'movies': movies})


def theaters_list_view(request):
    theaters = [
        {
            'name': 'Grand Cinema - Downtown',
            'city': 'Mumbai',
            'halls': 4,
            'address': '123 Main St',
            'image': 'https://i.pinimg.com/1200x/97/4a/0b/974a0bc3ef606c46538f46bfe41055ce.jpg'
        },
        {
            'name': 'Starlight Multiplex',
            'city': 'Pune',
            'halls': 6,
            'address': '45 Park Ave',
            'image': 'https://images.pexels.com/photos/109669/pexels-photo-109669.jpeg'
        },
        {
            'name': 'Galaxy Cinemas',
            'city': 'Delhi',
            'halls': 5,
            'address': '78 Cinema Road',
            'image': 'https://i.pinimg.com/1200x/d4/c6/eb/d4c6eb737f4f8f4ea97205bbe3d3608b.jpg'
        },
        {
            'name': 'Inox Crown',
            'city': 'Lucknow',
            'halls': 1,
            'address': 'Faizabad Rd Crown Mall',
            'image': 'https://www.shabdi.com/wp-content/uploads/INOX-Crown-Mall-Lucknow.jpg'
        },
    ]
    return render(request, 'theaters.html', {'theaters': theaters})
