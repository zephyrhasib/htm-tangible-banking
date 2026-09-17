# Audio Map

All clips are pre-generated and stored on the microSD card as `0001.mp3` … `0043.mp3`. The firmware plays them by number. Tracks 1–38 are Bangla speech (Microsoft Edge TTS, voice `bn-BD-NabanitaNeural`); 39–43 are synthesised tones.

**Loading order matters** — see SETUP.md Part 3.2. If track 1 plays the wrong clip, the card was written out of order.

## Guidance and session

| # | Bangla | Meaning | Plays when |
|---|---|---|---|
| 0001 | সবুজ এলাকায় আপনার কার্ডটি ছোঁয়ান | Tap your card in the green zone | reserved |
| 0002 | সবুজ এলাকায় আপনার নীল চাবিটি ছোঁয়ান | Tap your blue key in the green zone | any card tapped while locked |
| 0003 | স্বাগতম ফাতেমা বেগম | Welcome, Fatema Begum | keyfob unlock |
| 0004 | টাকার পরিমাণ বাড়াতে বারবার কার্ড ছোঁয়ান | Tap repeatedly to add to the amount | once per session, after first recipient |
| 0005 | যেমন, দুই হাজার টাকা পাঠাতে এক হাজার টাকার কার্ড দুইবার ছোঁয়ান | e.g. tap the 1000 card twice for 2000 | not used in final build |
| 0036 | নিশ্চিত করতে হলুদ বাটনটি চেপে ধরে রাখুন | Hold the yellow button to confirm | once per session when amount first > 0; also on early release |
| 0037 | কাজ শেষ হলে আবার চাবিটি ছোঁয়ান | When finished, touch the key again | reserved |
| 0038 | আপনার কাজ বন্ধ হলো | Your work is now closed | device locks |

## Recipients

| # | Bangla | Meaning |
|---|---|---|
| 0006 | আপনি টাকা পাঠানোর জন্য শান্তকে নির্বাচন করেছেন | You selected Shanto |
| 0007 | … তন্ময়কে … | You selected Tonmoy |
| 0008 | … কবিরকে … | You selected Kabir |
| 0009 | … পূজাকে … | You selected Puja |
| 0010 | … হাসিবকে … | You selected Hasib |

## Number building blocks

Amounts and balances are spoken by chaining **thousands + hundreds + টাকা**. Example: 1 700 → 0020 + 0017 + 0030.

| # | Hundreds | # | Thousands |
|---|---|---|---|
| 0011 | একশো (100) | 0020 | এক হাজার (1 000) |
| 0012 | দুইশো (200) | 0021 | দুই হাজার (2 000) |
| 0013 | তিনশো (300) | 0022 | তিন হাজার (3 000) |
| 0014 | চারশো (400) | 0023 | চার হাজার (4 000) |
| 0015 | পাঁচশো (500) | 0024 | পাঁচ হাজার (5 000) |
| 0016 | ছয়শো (600) | 0025 | ছয় হাজার (6 000) |
| 0017 | সাতশো (700) | 0026 | সাত হাজার (7 000) |
| 0018 | আটশো (800) | 0027 | আট হাজার (8 000) |
| 0019 | নয়শো (900) | 0028 | নয় হাজার (9 000) |
| | | 0029 | দশ হাজার (10 000) |

| # | Bangla | Meaning |
|---|---|---|
| 0030 | টাকা | taka (suffix) |
| 0031 | আপনার ব্যালেন্স | Your balance is … (prefix) |

## Status

| # | Bangla | Meaning | Plays when |
|---|---|---|---|
| 0032 | কার্ডটি চেনা যায়নি | Card not recognised | unknown UID |
| 0033 | ব্যালেন্স যথেষ্ট নয় | Insufficient balance | tap would exceed limit |
| 0034 | আপনার টাকা পাঠানো সফল হয়েছে | Your money was sent successfully | transfer complete |
| 0035 | লেনদেন বাতিল হয়েছে | Transaction cancelled | undo to zero; pink button mid-transaction |

## Sound effects (synthesised, `generate_sfx.py`)

| # | Sound | Used for |
|---|---|---|
| 0039 | short high beep | undo succeeded |
| 0040 | two-note descending buzz | any error / blocked / rejected / not-ready |
| 0041 | rising three-note chime | reserved |
| 0042 | soft click | reserved |
| 0043 | low double beep | reserved |
