from datetime import datetime, date, time, timedelta

# time_ = time(microsecond=1705138034222)
# date_time = datetime(second=1705138034222)
# print(time_)
# delta = timedelta(seconds=1705138034222)
# print(delta + datetime(year=1970, month=1, day=1))

date_time = datetime.fromtimestamp(1675328558.759).date()
print(date_time)