from datetime import datetime
import os

# after 30th June IST
LATE_REGISTRATION_START_DATE = datetime.strptime(
    "2020-07-01T00:00:00+05:30", "%Y-%m-%dT%H:%M:%S%z"
)
# after 10th July IST
USER_REGISTRATIOn_END_DATE = datetime.strptime(
    "2020-07-11T00:00:00+05:30", "%Y-%m-%dT%H:%M:%S%z"
)
QUESTION_TO_ASK = 3
QUIZ_TIME_LIMIT = int(os.getenv("QUIZ_TIME_LIMIT", 90))
QUIZ_PRIZE_AMOUNT = list(
    float(val)
    for val in os.getenv("QUIZ_PRIZE_AMOUNT", "137.5 112.5 100 75 75").split()
)
