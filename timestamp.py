from datetime import datetime,timezone

def create_timestamp(utc_timestamp = None):
    """time stamp in UTC (ISO 8601) format - used as secondary key in some DB operations"""
    if utc_timestamp is None:
        return datetime.utcnow().isoformat()[:-3]+'Z'
    else:
        return utc_timestamp.isoformat()[:-3]+'Z'
    
def parse_timestamp(time_str):
    """create datetime object from UTC (ISO 8601) string"""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
