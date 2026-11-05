| Action | Decision | Justification |
|---|---|---|
| 01 Read the appointments of a day | alone | Can't break anything with reading data |
| 02 Look up the weather | alone | Can't break anything with reading data |
| 03 Search train connections | alone | Can't break anything with reading data |
| 04 Read Notes | alone | Can't break anything with reading data |
| 05 Create a personal block in a calender | approval | Could lead to conflicts |
| 06 Reschedule an appointment with other attendees | approval | Need also the approval of the attendees |
| 07 Book a train ticket | approval | Costs money |
| 08 Send a message to third parties | approval | Misunderstanding could lead to unwanted messages |
| 09 Create a Note | alone | No harm in notes. Agent could have its own notes |
| 10 Delete a Note | approval | DOnt want to delete inmportant notes |

## Rule

When changing or deleting a file you will always have to get an approval.
Things like buying a ticket cost money. Buying things will always need an approval.
Reading cant break anything. The result could be worse because he read something that was not necessary.
Creating text files could be allowed, but should be specified in a system prompt.

## Observations

- I forgot to tell the price. Agents can withhold crucial information.
- Information for events could be at different places (i.e. calendar and notes).

