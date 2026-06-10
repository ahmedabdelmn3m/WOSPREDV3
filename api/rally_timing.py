"""
Rally Timing Calculator API
Endpoints for synchronized rally launch calculations
"""

from pydantic import BaseModel
from typing import List, Optional
from fastapi import HTTPException

class RallyLeaderInput(BaseModel):
    name: str
    march_time_str: str  # "m:ss" format
    rally_fill_minutes: int  # 1, 5, 10, 15, 20
    hit_order: int  # 1 = first to hit

class RallyTimingRequest(BaseModel):
    leaders: List[RallyLeaderInput]

class RallyCalculation(BaseModel):
    leader_name: str
    march_time_ms: int
    rally_fill_ms: int
    hit_order: int
    launch_time_formatted: str
    hit_time_formatted: str
    offset_from_first_formatted: str
    instruction: str

class RallyTimingResponse(BaseModel):
    calculations: List[RallyCalculation]
    summary: str

def parse_time_to_ms(time_str: str) -> int:
    """Parse m:ss or mm:ss to milliseconds"""
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid time format. Use m:ss or mm:ss")
    
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except ValueError:
        raise ValueError("Invalid time values")
    
    if seconds >= 60:
        raise ValueError("Seconds must be less than 60")
    
    return minutes * 60 * 1000 + seconds * 1000

def format_ms_to_time(ms: int) -> str:
    """Convert milliseconds to m:ss format"""
    total_seconds = round(ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"

def calculate_rally_timing(leaders: List[RallyLeaderInput]) -> RallyTimingResponse:
    """
    Calculate rally timing for all leaders
    
    Algorithm:
    1. Parse march times and rally fill times
    2. Calculate hit times based on hit order
    3. Calculate launch times (hit time - march time - rally fill time)
    4. Find earliest launch time
    5. Calculate offsets from first leader
    """
    
    if not leaders:
        raise ValueError("At least one leader is required")
    
    if len(leaders) > 5:
        raise ValueError("Maximum 5 leaders allowed")
    
    # Validate hit orders
    hit_orders = [l.hit_order for l in leaders]
    if len(set(hit_orders)) != len(hit_orders):
        raise ValueError("Duplicate hit orders detected")
    
    for leader in leaders:
        if leader.hit_order < 1 or leader.hit_order > len(leaders):
            raise ValueError(f"Invalid hit order for {leader.name}")
    
    # Parse times
    march_times_ms = []
    rally_fill_ms = []
    
    for leader in leaders:
        try:
            march_ms = parse_time_to_ms(leader.march_time_str)
            march_times_ms.append(march_ms)
            rally_fill_ms.append(leader.rally_fill_minutes * 60 * 1000)
        except ValueError as e:
            raise ValueError(f"Error parsing times for {leader.name}: {str(e)}")
    
    # Sort by hit order
    sorted_indices = sorted(range(len(leaders)), key=lambda i: leaders[i].hit_order)
    sorted_leaders = [leaders[i] for i in sorted_indices]
    sorted_march_times = [march_times_ms[i] for i in sorted_indices]
    sorted_rally_fills = [rally_fill_ms[i] for i in sorted_indices]
    
    # Calculate hit times (each leader hits 0.5s after the previous)
    hit_times = []
    for i in range(len(sorted_leaders)):
        hit_times.append(i * 500)  # 0.5s intervals
    
    # Calculate launch times
    launch_times = []
    for i in range(len(sorted_leaders)):
        launch_time = hit_times[i] - sorted_march_times[i] - sorted_rally_fills[i]
        launch_times.append(launch_time)
    
    # Find earliest launch time
    earliest_launch = min(launch_times)
    
    # Build calculations
    calculations = []
    for i in range(len(sorted_leaders)):
        leader = sorted_leaders[i]
        offset_from_first = launch_times[i] - earliest_launch
        
        # Generate instruction
        if offset_from_first == 0:
            instruction = f"{leader.name} launches FIRST"
        else:
            delay_seconds = round(offset_from_first / 1000)
            instruction = f"{leader.name} waits {delay_seconds}s, then launches ({format_ms_to_time(offset_from_first)} after {sorted_leaders[0].name})"
        
        calculations.append(RallyCalculation(
            leader_name=leader.name,
            march_time_ms=sorted_march_times[i],
            rally_fill_ms=sorted_rally_fills[i],
            hit_order=leader.hit_order,
            launch_time_formatted=format_ms_to_time(max(0, launch_times[i])),
            hit_time_formatted=format_ms_to_time(hit_times[i]),
            offset_from_first_formatted=format_ms_to_time(max(0, offset_from_first)),
            instruction=instruction
        ))
    
    # Generate summary
    first_hit = min(hit_times)
    last_hit = max(hit_times)
    total_duration = last_hit - first_hit
    
    if len(calculations) == 1:
        summary = f"{calculations[0].leader_name} hits at {format_ms_to_time(first_hit)}"
    else:
        summary = f"All leaders hit within {format_ms_to_time(total_duration)} ({len(calculations)} rallies)"
    
    return RallyTimingResponse(
        calculations=calculations,
        summary=summary
    )
