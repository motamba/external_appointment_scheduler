(function () {
    // Lightweight API wrapper for appointment frontend
    window.AppointmentAPI = {
        getAvailability: function (serviceId) {
            return fetch('/api/appointments/availability?service_id=' + encodeURIComponent(serviceId), {
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' }
            }).then(function (r) { return r.json(); });
        },
        bookAppointment: function (payload) {
            return fetch('/api/appointments/book', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            }).then(function (r) { return r.json(); });
        }
    };
})();
