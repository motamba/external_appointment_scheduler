(function () {
    // Lightweight API wrapper for appointment frontend
    console.log('[AppointmentAPI] Initializing API wrapper');
    window.AppointmentAPI = {
        getAvailability: function (serviceId) {
            console.log('[AppointmentAPI] Fetching availability for service:', serviceId);
            return fetch('/api/appointments/availability?service_id=' + encodeURIComponent(serviceId), {
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' }
            }).then(function (r) { 
                console.log('[AppointmentAPI] Response status:', r.status);
                return r.json(); 
            }).then(function(data) {
                console.log('[AppointmentAPI] Parsed data:', data);
                return data;
            });
        },
        bookAppointment: function (payload) {
            console.log('[AppointmentAPI] Booking appointment with payload:', payload);
            return fetch('/api/appointments/book', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            }).then(function (r) { 
                console.log('[AppointmentAPI] Booking response status:', r.status);
                return r.json(); 
            }).then(function(data) {
                console.log('[AppointmentAPI] Booking response data:', data);
                return data;
            });
        }
    };
    console.log('[AppointmentAPI] API wrapper initialized successfully');
})();
