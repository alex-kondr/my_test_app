from datetime import datetime, timedelta


end_date = "2024-09-02"
time_delta = timedelta(7)

parse_date = datetime.strptime(end_date, "%Y-%m-%d")
end_date = str(parse_date.date() - time_delta)
print(end_date)