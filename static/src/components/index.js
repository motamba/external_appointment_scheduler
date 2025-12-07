/** @odoo-module **/

import { registry } from "@web/core/registry";
import { AppointmentCalendar } from "./components/appointment_calendar/appointment_calendar_owl";

// Register the appointment calendar widget for use in backend views
registry.category("fields").add("appointment_calendar_widget", {
    component: AppointmentCalendar,
});

export { AppointmentCalendar };
export { SlotPicker } from "./components/slot_picker/slot_picker_owl";
export { BookingForm } from "./components/booking_form/booking_form_owl";
