/** @odoo-module **/

import { Component } from "@odoo/owl";

export class SlotPicker extends Component {
    static template = "external_appointment_scheduler.SlotPicker";
    static props = {
        slots: { type: Array },
        onSlotSelected: { type: Function },
    };

    selectSlot(slot) {
        this.props.onSlotSelected(slot);
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }
}
