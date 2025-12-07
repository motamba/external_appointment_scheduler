/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class BookingForm extends Component {
    static template = "external_appointment_scheduler.BookingForm";
    static props = {
        slot: { type: Object },
        onSubmit: { type: Function },
        onCancel: { type: Function },
    };

    setup() {
        this.state = useState({
            name: "",
            email: "",
            phone: "",
            notes: "",
            submitting: false,
        });
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    async onSubmitForm(ev) {
        ev.preventDefault();
        
        if (!this.state.name || !this.state.email) {
            return;
        }

        this.state.submitting = true;

        try {
            await this.props.onSubmit({
                slot: this.props.slot,
                name: this.state.name,
                email: this.state.email,
                phone: this.state.phone,
                notes: this.state.notes,
            });
        } finally {
            this.state.submitting = false;
        }
    }

    onCancelForm() {
        this.props.onCancel();
    }
}
