from datetime import datetime, timedelta

# Standard date format for string representation
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format into a datetime object.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        datetime object
        
    Raises:
        ValueError if date string is invalid
    """
    return datetime.strptime(date_str, DATE_FORMAT)

def parse_datetime(datetime_str: str) -> datetime:
    """Parse a datetime string in YYYY-MM-DD HH:MM:SS format into a datetime object.
    
    Args:
        datetime_str: Datetime string in YYYY-MM-DD HH:MM:SS format
        
    Returns:
        datetime object
        
    Raises:
        ValueError if datetime string is invalid
    """
    return datetime.strptime(datetime_str, DATETIME_FORMAT)

def format_date(date: datetime) -> str:
    """Format a datetime object as YYYY-MM-DD string.
    
    Args:
        date: datetime object
        
    Returns:
        Formatted date string
    """
    return date.strftime(DATE_FORMAT)

def format_datetime(date: datetime) -> str:
    """Format a datetime object as YYYY-MM-DD HH:MM:SS string.
    
    Args:
        date: datetime object
        
    Returns:
        Formatted datetime string
    """
    return date.strftime(DATETIME_FORMAT)

def get_start_of_day(date: datetime) -> datetime:
    """Get datetime object representing start of the given date (00:00:00).
    
    Args:
        date: datetime object
        
    Returns:
        datetime object set to start of day
    """
    return datetime.combine(date.date(), datetime.min.time())

def get_end_of_day(date: datetime) -> datetime:
    """Get datetime object representing end of the given date (23:59:59).
    
    Args:
        date: datetime object
        
    Returns:
        datetime object set to end of day
    """
    return datetime.combine(date.date(), datetime.max.time())

def get_date_range(days: int = 30) -> tuple[datetime, datetime]:
    """Get start and end dates for a date range ending today.
    
    Args:
        days: Number of days to look back (default 30)
        
    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

def parse_date_range(start_date_str: str | None, end_date_str: str | None, default_days: int = 30) -> tuple[datetime, datetime]:
    """Parse start and end date strings, with fallback to default range.
    
    Args:
        start_date_str: Start date string in YYYY-MM-DD format, or None
        end_date_str: End date string in YYYY-MM-DD format, or None
        default_days: Default number of days to look back if dates not provided
        
    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    try:
        if start_date_str and end_date_str:
            start_date = get_start_of_day(parse_date(start_date_str))
            end_date = get_end_of_day(parse_date(end_date_str))
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=default_days)
            
        return start_date, end_date
    except ValueError:
        # If date parsing fails, return default range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=default_days)
        return start_date, end_date 