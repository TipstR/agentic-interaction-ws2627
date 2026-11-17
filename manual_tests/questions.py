"""Typical questions for the calendar agent, with what a correct answer looks like.

The expectations assume today = Wednesday 2026-10-28 (the default of the runner).
Mock calendar 2026-10-26..2026-11-08:
  10-29  09:00-10:00 Standup Projektteam (O27/3302)
         11:00-12:30 Werkstattbesuch Prototyp (Muenchen, Werk 2)
         16:00-17:00 Rueckmeldung an Betreuerin (online)
  11-02  14:00-15:30 Pruefungsbesprechung (O28/1002)
  11-03  all day     Abgabefrist Hausarbeit (no location)
  every other day in the range is empty; outside the range -> HTTP 404 (no data)
"""

QUESTIONS = [
    {"id": 1, "category": "Basic",
     "question": "Was steht am 29.10.2026 im Kalender?",
     "expect": "All 3 appointments of 2026-10-29 with time and location, answered in German."},
    {"id": 2, "category": "Basic / language",
     "question": "What's on my calendar on November 2nd, 2026?",
     "expect": "Answer in English: Pruefungsbesprechung 14:00-15:30, O28/1002."},
    {"id": 3, "category": "All-day",
     "question": "Habe ich am 3.11.2026 Termine?",
     "expect": "Abgabefrist Hausarbeit as an all-day item; no invented time or location."},
    {"id": 4, "category": "Empty day",
     "question": "Was steht am 31.10.2026 an?",
     "expect": "Says there are no appointments (the day has data, the list is empty)."},
    {"id": 5, "category": "No data",
     "question": "Was steht am 15.12.2026 im Kalender?",
     "expect": "Says there is no data for that day. Must NOT claim the day is free."},
    {"id": 6, "category": "Relative date",
     "question": "Was habe ich heute?",
     "expect": "Looks up 2026-10-28; no appointments."},
    {"id": 7, "category": "Relative date",
     "question": "Habe ich morgen Termine?",
     "expect": "Looks up 2026-10-29; lists the 3 appointments."},
    {"id": 8, "category": "Relative date",
     "question": "Was steht am Freitag an?",
     "expect": "Looks up 2026-10-30; no appointments."},
    {"id": 9, "category": "Relative date",
     "question": "Was habe ich nächsten Montag?",
     "expect": "Looks up 2026-11-02; Pruefungsbesprechung 14:00-15:30, O28/1002."},
    {"id": 10, "category": "Multi-day",
     "question": "Welche Termine habe ich diese Woche?",
     "expect": "One tool call per day (2026-10-26..11-01, or the rest of the week); lists the 10-29 appointments."},
    {"id": 11, "category": "Multi-day",
     "question": "Was ist mein nächster Termin nach dem 29.10.2026?",
     "expect": "Checks the following days and stops at 2026-11-02 (Pruefungsbesprechung), within the step limit."},
    {"id": 12, "category": "Reasoning",
     "question": "Bin ich am 29.10.2026 um 11:30 frei?",
     "expect": "No: Werkstattbesuch Prototyp 11:00-12:30."},
    {"id": 13, "category": "Hallucination",
     "question": "Wo findet die Prüfungsbesprechung statt?",
     "expect": "No date given: looks up days or asks for the date. Never invents a room."},
    {"id": 14, "category": "Invalid input",
     "question": "Was steht am 31.02.2026 an?",
     "expect": "Explains the date does not exist; no crash, no guessed appointments."},
    {"id": 15, "category": "Ambiguous",
     "question": "Was steht im Kalender?",
     "expect": "Assumes today (2026-10-28) and says so, or asks which day."},
    {"id": 16, "category": "Out of scope",
     "question": "Trag mir morgen um 10 Uhr einen Zahnarzttermin ein.",
     "expect": "Says it cannot create appointments. Must NOT claim it did."},
    {"id": 17, "category": "Out of scope",
     "question": "Wie wird das Wetter morgen in Ulm?",
     "expect": "Says it has no weather access; no invented forecast."},
]
