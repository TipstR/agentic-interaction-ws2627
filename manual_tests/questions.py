"""Typical questions for the calendar agent, with what a correct answer looks like.

The expectations assume today = Wednesday 2026-10-28 (the default of the runner).
Mock calendar 2026-10-26..2026-11-08:
  10-29  09:00-10:00 Standup Projektteam (O27/3302)
         11:00-12:30 Werkstattbesuch Prototyp (Muenchen, Werk 2)
         16:00-17:00 Rueckmeldung an Betreuerin (online)
  11-02  14:00-15:30 Pruefungsbesprechung (O28/1002)
  11-03  all day     Abgabefrist Hausarbeit (no location)
  every other day in the range is empty; outside the range -> HTTP 404 (no data)

Weather exists only for: ulm 10-29, 10-30, 11-02, 11-03; muenchen 10-29, 11-02.
Connections exist only for: ulm->muenchen 10-29, 11-02; muenchen->ulm 10-29.
  ulm->muenchen 10-29: 07:12-08:31 ICE 594, 08:12-09:33 ICE 596,
                       08:44-10:28 RE 57412 (1 change), 09:12-10:31 ICE 598
  muenchen->ulm 10-29: 13:28-14:47 ICE 591, 15:28-16:47 ICE 593
  weather 10-29: Ulm Regen 9 °C 80 %; München Schauer 8 °C 60 %
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
    {"id": 17, "category": "Weather",
     "question": "Wie wird das Wetter morgen in Ulm?",
     "expect": "get_weather(Ulm, 2026-10-29): Regen, 9 °C, 80 % rain, wind 24 km/h."},
    # --- Exercise 4: weather and train connections ---
    {"id": 18, "category": "Two tools",
     "question": "How do I get to Munich on 29 Oct 2026, and do I need an umbrella?",
     "expect": "get_connections(Ulm, München) + get_weather(München): names trains/departures "
               "(e.g. ICE 594 07:12) AND the weather (Schauer, 8 °C, 60 %) -> yes, umbrella. "
               "Says it assumed Ulm as start."},
    {"id": 19, "category": "Two tools",
     "question": "Ich muss morgen um 11 Uhr in München sein. Welchen Zug nehme ich und wie wird das Wetter dort?",
     "expect": "Train arriving before 11:00 (ICE 598 09:12->10:31 or earlier) and Munich weather "
               "(Schauer, 8 °C)."},
    {"id": 20, "category": "Three tools",
     "question": "Was habe ich am 29.10.2026 in München vor, wie komme ich hin und zurück, und brauche ich einen Schirm?",
     "expect": "Werkstattbesuch 11:00-12:30; outbound train arriving before 11:00, return "
               "München->Ulm (ICE 591 13:28 or ICE 593 15:28); Munich weather -> umbrella yes."},
    {"id": 21, "category": "Gap: day",
     "question": "Wie komme ich am 30.10.2026 nach München und wie wird dort das Wetter?",
     "expect": "No connections and no Munich weather for 10-30: says so. Invents no trains, "
               "times or temperatures (may mention the Ulm forecast if it looked it up)."},
    {"id": 22, "category": "Gap: place",
     "question": "Wie wird das Wetter am 29.10.2026 in Berlin und gibt es einen Zug von Ulm dorthin?",
     "expect": "No data for Berlin (weather or trains). No invented values."},
    {"id": 23, "category": "Gap: partial",
     "question": "Fährt am 2.11.2026 ein Zug von München nach Ulm, und wie ist das Wetter in Ulm?",
     "expect": "No connections München->Ulm on 11-02 (only Ulm->München exists): says so. "
               "Ulm weather comes from the tool, not invented."},
    {"id": 24, "category": "Weather only",
     "question": "Brauche ich am 3.11.2026 in Ulm einen Regenschirm?",
     "expect": "Answer based on get_weather(Ulm, 2026-11-03); clear yes/no matching rain probability."},
]
