(function () {
    // Simple booking widget initializer (lightweight, not full OWL yet)
    function mountBookingWidget(container) {
        var serviceId = container.getAttribute('data-service-id');
        if (!serviceId) {
            container.innerHTML = '<div class="alert alert-warning">Service not specified.</div>';
            return;
        }
        container.innerHTML = '<div class="ea-calendar-widget"><div class="ea-slot-picker" aria-live="polite">Loading availability...</div><div class="ea-booking-form"></div></div>';
        var slotPickerEl = container.querySelector('.ea-slot-picker');
        var bookingFormEl = container.querySelector('.ea-booking-form');

        // Check if API is available
        if (typeof window.AppointmentAPI === 'undefined') {
            slotPickerEl.innerHTML = '<div class="alert alert-danger">Appointment API not loaded. Please refresh the page.</div>';
            console.error('AppointmentAPI is not defined');
            return;
        }

        // Load availability
        console.log('Loading availability for service:', serviceId);
        AppointmentAPI.getAvailability(serviceId).then(function (data) {
            console.log('Availability data:', data);
            if (!data) {
                slotPickerEl.innerHTML = '<div class="alert alert-danger">Failed to load availability. Please contact support.</div>';
                return;
            }
            if (data.error) {
                slotPickerEl.innerHTML = '<div class="alert alert-danger">Error: ' + data.error + '</div>';
                return;
            }
            if (!data.success || !data.slots || data.slots.length === 0) {
                slotPickerEl.innerHTML = '<div class="alert alert-info">No available slots found for the next 7 days. Please check back later or contact us.</div>';
                return;
            }
            // Render slots
            slotPickerEl.innerHTML = '';
            data.slots.forEach(function (slot) {
                var btn = document.createElement('button');
                btn.className = 'btn btn-outline-primary btn-block ea-slot-item mb-2';
                btn.type = 'button';
                btn.textContent = slot.start_display + ' — ' + slot.end_display + (slot.capacity ? (' (' + slot.capacity + ' spots)') : '');
                btn.dataset.slotId = slot.id;
                btn.dataset.start = slot.start;
                btn.dataset.end = slot.end;
                btn.addEventListener('click', function () {
                    // render booking form
                    renderBookingForm(bookingFormEl, serviceId, slot);
                });
                slotPickerEl.appendChild(btn);
            });
        }).catch(function (err) {
            slotPickerEl.innerHTML = '<div class="alert alert-danger">Error loading availability</div>';
            console.error(err);
        });
    }

    function renderBookingForm(container, serviceId, slot) {
        container.innerHTML = '';
        var html = '';
        html += '<form class="ea-booking-form-inner">';
        html += '<div class="form-group">';
        html += '<label>Name</label><input name="name" class="form-control" required />';
        html += '</div>';
        html += '<div class="form-group">';
        html += '<label>Email</label><input name="email" type="email" class="form-control" required />';
        html += '</div>';
        html += '<div class="form-group">';
        html += '<label>Phone</label><input name="phone" class="form-control" />';
        html += '</div>';
        html += '<div class="form-group">';
        html += '<label>Notes</label><textarea name="notes" class="form-control" rows="3"></textarea>';
        html += '</div>';
        html += '<div class="form-group text-right">';
        html += '<button type="submit" class="btn btn-primary">Confirm Booking</button>';
        html += '</div>';
        html += '</form>';
        container.innerHTML = html;

        var form = container.querySelector('form');
        form.addEventListener('submit', function (ev) {
            ev.preventDefault();
            var formData = new FormData(form);
            var payload = {
                service_id: parseInt(serviceId, 10),
                slot_id: slot.id || null,
                start: slot.start,
                end: slot.end,
                customer_name: formData.get('name'),
                customer_email: formData.get('email'),
                customer_phone: formData.get('phone'),
                notes: formData.get('notes')
            };
            // disable submit
            var btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Booking...';
            AppointmentAPI.bookAppointment(payload).then(function (res) {
                if (res && res.success) {
                    container.innerHTML = '<div class="alert alert-success">Booking confirmed! Reference: ' + (res.reference || res.id) + '</div>';
                } else {
                    btn.disabled = false;
                    btn.textContent = 'Confirm Booking';
                    container.insertAdjacentHTML('afterbegin', '<div class="alert alert-danger">' + (res.error || 'Booking failed') + '</div>');
                }
            }).catch(function (err) {
                btn.disabled = false;
                btn.textContent = 'Confirm Booking';
                container.insertAdjacentHTML('afterbegin', '<div class="alert alert-danger">Booking error</div>');
                console.error(err);
            });
        });
    }

    // Auto-mount on portal page
    document.addEventListener('DOMContentLoaded', function () {
        var container = document.getElementById('appointment-booking-widget');
        if (container) {
            mountBookingWidget(container);
        }
    });
})();
