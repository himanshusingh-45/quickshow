// static/js/seats.js
(function () {
  const seatLayout = [
    { row: 'A', count: 9 },
    { row: 'B', count: 9 },
    { type: 'aisle' },
    { row: 'C', count: 9, section: 'left' },
    { row: 'D', count: 9, section: 'left' },
    { row: 'E', count: 9, section: 'right' },
    { row: 'F', count: 9, section: 'right' },
    { type: 'aisle' },
    { row: 'G', count: 9, section: 'left' },
    { row: 'H', count: 9, section: 'left' },
    { row: 'I', count: 9, section: 'right' },
    { row: 'J', count: 9, section: 'right' },
  ];

  // prefer server-injected window.OCCUPIED_SEATS, else fallback empty
  const occupiedSeatsGlobal = (window.OCCUPIED_SEATS && Array.isArray(window.OCCUPIED_SEATS))
    ? window.OCCUPIED_SEATS
    : [];

  // if template provides initial_booked_seats array, prefer that for initial rendering
  const initialBookedFromTemplate = (typeof initial_booked_seats !== 'undefined' && Array.isArray(initial_booked_seats))
    ? initial_booked_seats
    : [];

  // merge both sources (template preferred)
  const occupiedSeats = initialBookedFromTemplate.length ? initialBookedFromTemplate : occupiedSeatsGlobal;

  function buildSeatingGrid(containerId = 'seating-grid') {
    const seatingGrid = document.getElementById(containerId);
    if (!seatingGrid) return;

    seatingGrid.innerHTML = '';
    let currentBlock = document.createElement('div');
    currentBlock.className = 'seat-block';

    seatLayout.forEach(config => {
      if (config.type === 'aisle') {
        seatingGrid.appendChild(currentBlock);
        currentBlock = document.createElement('div');
        currentBlock.className = 'seat-block';
        return;
      }

      let column = currentBlock.querySelector(`.seat-column[data-section="${config.section || 'center'}"]`);
      if (!column) {
        column = document.createElement('div');
        column.className = 'seat-column';
        column.setAttribute('data-section', config.section || 'center');
        currentBlock.appendChild(column);
      }

      const rowDiv = document.createElement('div');
      rowDiv.className = 'seat-row';
      rowDiv.setAttribute('aria-label', `Row ${config.row}`);

      for (let i = 1; i <= config.count; i++) {
        const seatId = `${config.row}${i}`;
        const seat = document.createElement('button');
        seat.type = 'button';
        seat.className = 'seat';
        seat.textContent = seatId;

        // set both attributes so different codepaths can find it
        seat.setAttribute('data-seat-id', seatId);
        seat.setAttribute('data-seat', seatId);

        // accessible state
        seat.setAttribute('aria-pressed', 'false');
        seat.setAttribute('data-available', 'true');

        // mark occupied if present in injected array
        if (occupiedSeats && occupiedSeats.includes(seatId)) {
          // use the same class your template's markBookedSeats expects
          seat.classList.add('seat-booked');
          seat.disabled = true;
          seat.setAttribute('aria-disabled', 'true');
          seat.setAttribute('data-available', 'false');
          // also add 'occupied' class for backward compatibility
          seat.classList.add('occupied');
          seat.style.opacity = '0.35';
          seat.style.pointerEvents = 'none';
        }

        rowDiv.appendChild(seat);
      }

      column.appendChild(rowDiv);
    });

    seatingGrid.appendChild(currentBlock);
  }

  function attachSeatHandlers(containerId = 'seating-grid') {
    const seatingGrid = document.getElementById(containerId);
    if (!seatingGrid) return;

    seatingGrid.addEventListener('click', function (e) {
      const btn = e.target.closest('.seat');
      if (!btn || btn.classList.contains('occupied') || btn.classList.contains('seat-booked') || btn.disabled) return;
      const selected = btn.classList.toggle('selected');
      btn.setAttribute('aria-pressed', selected ? 'true' : 'false');
    });
  }

  function attachTimingHandlers(timingsId = 'timings-list') {
    const timingsList = document.getElementById(timingsId);
    if (!timingsList) return;
    timingsList.addEventListener('click', (e) => {
      const slot = e.target.closest('.time-slot');
      if (!slot || slot.classList.contains('no-shows')) return;
      const prev = timingsList.querySelector('.time-slot.active');
      if (prev) prev.classList.remove('active');
      slot.classList.add('active');

      // when show changes, fetch booked seats for that show if endpoint exists
      const sid = slot.getAttribute('data-show-id');
      if (sid) fetchAndMarkBookedSeats(sid);
    });
  }

  function getSelectedSeats() {
    return Array.from(document.querySelectorAll('.seat.selected'))
      .map(s => (s.dataset.seatId || s.getAttribute('data-seat') || s.textContent || '').trim())
      .filter(Boolean);
  }

  function getActiveShow() {
    const slot = document.querySelector('#timings-list .time-slot.active:not(.no-shows)');
    if (!slot) return null;
    const showId = slot.dataset.showId || '';
    const showText = slot.querySelector('.meta') ? slot.querySelector('.meta').innerText.trim() : slot.innerText.trim();
    return { showId: (showId || '').toString(), showText };
  }

  // fetch booked seats from your API endpoint and mark them
  async function fetchAndMarkBookedSeats(showId) {
    if (!showId) return;
    try {
      const res = await fetch(`/api/show/${showId}/booked_seats/`);
      if (!res.ok) return;
      const data = await res.json();
      markBookedSeats(data.booked || []);
    } catch (err) {
      console.error('fetchBookedSeats error', err);
    }
  }

  function markBookedSeats(list) {
    const setB = new Set(list || []);
    document.querySelectorAll('[data-seat], [data-seat-id]').forEach(el => {
      const id = el.getAttribute('data-seat') || el.getAttribute('data-seat-id') || '';
      if (!id) return;
      if (setB.has(id)) {
        el.classList.add('seat-booked');
        el.classList.add('occupied');
        el.setAttribute('aria-disabled', 'true');
        el.setAttribute('data-available', 'false');
        el.disabled = true;
        el.style.opacity = '0.35';
        el.style.pointerEvents = 'none';
      } else {
        el.classList.remove('seat-booked');
        el.classList.remove('occupied');
        el.removeAttribute('aria-disabled');
        el.setAttribute('data-available', 'true');
        el.disabled = false;
        el.style.opacity = '';
        el.style.pointerEvents = '';
      }
    });
  }

  // When DOM ready
  document.addEventListener('DOMContentLoaded', function () {
    buildSeatingGrid();
    attachSeatHandlers();
    attachTimingHandlers();

    // expose helpers
    window.getSelectedSeats = getSelectedSeats;
    window.getActiveShow = getActiveShow;
    window.markBookedSeats = markBookedSeats;
    window.fetchAndMarkBookedSeats = fetchAndMarkBookedSeats;

    // If server-injected initial seats exist in template variable initial_booked_seats, use them.
    try {
      if (typeof initial_booked_seats !== 'undefined' && Array.isArray(initial_booked_seats) && initial_booked_seats.length > 0) {
        markBookedSeats(initial_booked_seats);
        return;
      }
    } catch (e) {
      // ignore
    }

    // fallback: if there's an active timing slot, fetch its booked seats
    const active = document.querySelector('#timings-list .time-slot.active[data-show-id]');
    if (active) {
      const sid = active.getAttribute('data-show-id');
      if (sid) fetchAndMarkBookedSeats(sid);
    } else if (occupiedSeatsGlobal && occupiedSeatsGlobal.length) {
      // fallback to global occupied array if present
      markBookedSeats(occupiedSeatsGlobal);
    }
  });
})();
