(function () {
    // Simple booking form helper. Used by appointment_calendar.
    window.EABookingForm = {
        render: function (container, serviceId, slot, onBooked) {
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
                var btn = form.querySelector('button[type="submit"]');
                btn.disabled = true;
                btn.textContent = 'Booking...';
                AppointmentAPI.bookAppointment(payload).then(function (res) {
                    if (res && res.success) {
                        container.innerHTML = '<div class="alert alert-success">Booking confirmed! Reference: ' + (res.reference || res.id) + '</div>';
                        if (typeof onBooked === 'function') { onBooked(res); }
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
    };
})();
