"""Benchmark tasks. Each has an expected end state so success is checked, not judged."""

TASKS = {
    "pharmacy-refill": {
        "persona_goal": "Refill your blood pressure pills (lisinopril) and pick them up Thursday afternoon.",
        "sut_context": ("You are a pharmacy assistant. The customer has refills for lisinopril 10mg "
                        "and atorvastatin 20mg. Pickup slots: Wed 10am, Thu 2pm, Thu 5pm, Fri 9am."),
        "expected": ["lisinopril", "thursday"],
    },
    "benefits-appointment": {
        "persona_goal": "Book an appointment to renew your Medicare Savings Program benefits, any weekday morning.",
        "sut_context": ("You are a benefits office assistant. Renewal appointments exist Mon 9am, Tue 1pm, "
                        "Wed 11am. The client must bring ID and a recent bank statement."),
        "expected": ["renew", "am"],
    },
}
