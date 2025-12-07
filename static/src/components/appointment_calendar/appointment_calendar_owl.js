/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { SlotPicker } from "../slot_picker/slot_picker";
import { BookingForm } from "../booking_form/booking_form";

export class AppointmentCalendar extends Component {
    static template = "external_appointment_scheduler.AppointmentCalendar";
    static components = { SlotPicker, BookingForm };
    static props = {
        serviceId: { type: Number },
    };

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.state = useState({
            slots: [],
            selectedSlot: null,
            loading: true,
            error: null,
            bookingComplete: false,
            bookingReference: null,
        });

        onWillStart(async () => {
            await this.loadAvailability();
        });
    }

    async loadAvailability() {
        this.state.loading = true;
        this.state.error = null;
        
        try {
            const response = await fetch(
                `/api/appointments/availability?service_id=${this.props.serviceId}`,
                {
                    credentials: 'same-origin',
                    headers: { 'Accept': 'application/json' }
                }
            );
            
            const data = await response.json();
            
            if (data.error) {
                this.state.error = data.error;
                this.state.slots = [];
            } else {
                this.state.slots = data.slots || [];
            }
        } catch (error) {
            console.error("Failed to load availability:", error);
            this.state.error = "Failed to load availability. Please try again.";
            this.state.slots = [];
        } finally {
            this.state.loading = false;
        }
    }

    onSlotSelected(slot) {
        this.state.selectedSlot = slot;
    }

    async onBookingSubmitted(bookingData) {
        try {
            const payload = {
                service_id: this.props.serviceId,
                slot_id: bookingData.slot.id || null,
                start: bookingData.slot.start,
                end: bookingData.slot.end,
                customer_name: bookingData.name,
                customer_email: bookingData.email,
                customer_phone: bookingData.phone,
                notes: bookingData.notes,
            };

            const response = await fetch('/api/appointments/book', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.state.bookingComplete = true;
                this.state.bookingReference = result.reference || result.id;
                this.notification.add("Appointment booked successfully!", {
                    type: "success",
                });
            } else {
                throw new Error(result.error || "Booking failed");
            }
        } catch (error) {
            console.error("Booking error:", error);
            this.notification.add(error.message || "Failed to book appointment", {
                type: "danger",
            });
        }
    }

    onBackToSlots() {
        this.state.selectedSlot = null;
    }

    async onRefresh() {
        await this.loadAvailability();
    }
}
