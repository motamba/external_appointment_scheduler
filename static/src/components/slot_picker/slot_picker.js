(function () {
    // Standalone slot picker used by the booking widget (currently included via appointment_calendar)
    window.EASlotPicker = {
        render: function (container, slots, onSelect) {
            container.innerHTML = '';
            if (!slots || slots.length === 0) {
                container.innerHTML = '<div class="alert alert-info">No available slots.</div>';
                return;
            }
            slots.forEach(function (slot) {
                var el = document.createElement('div');
                el.className = 'ea-slot-item mb-2';
                el.innerHTML = '<button type="button" class="btn btn-outline-primary btn-block">' + slot.start_display + ' — ' + slot.end_display + '</button>';
                el.querySelector('button').addEventListener('click', function () { onSelect(slot); });
                container.appendChild(el);
            });
        }
    };
})();
