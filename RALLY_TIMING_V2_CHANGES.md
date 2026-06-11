# Rally Timing Calculator v2 - Changes Summary

## What Changed

### ❌ Removed
- **UTC Impact Time**: No more confusing UTC timestamps
- **Troop Calculator**: Removed stat input fields and calculations
- **Info Section**: Replaced with practical "How to USE" guide

### ✅ Added
- **Launch Order Focus**: Simple "who launches first" logic
- **Timing Offsets**: Clear "wait X seconds after Y" instructions
- **How to USE Guide**: Step-by-step instructions for end users
- **Simplified UI**: Clean, focused interface with only essential inputs

---

## How It Works Now

### User Input
1. **Add Leaders** - Name and march time (seconds)
2. **Set Hitting Order** - Choose sequence (e.g., Alpha → Beta → Gamma)
3. **Set Hit Spacing** - Seconds between each hit (0 = simultaneous)
4. **Calculate** - Get launch sequence

### Output
```
✅ Launch Sequence

Instructions: Alpha launches first. Beta waits 2.0s after Alpha, then launches. Gamma waits 2.0s after Beta, then launches.

1. Alpha
   Leader: Alpha
   Launch At: 0.0s
   Wait instruction: Launch immediately

2. Beta
   Leader: Beta
   Launch At: 2.0s
   Wait instruction: Wait 2.0s after Alpha launches

3. Gamma
   Leader: Gamma
   Launch At: 4.0s
   Wait instruction: Wait 2.0s after Beta launches
```

---

## API Endpoints

### POST `/rally/calculate-v2`

**Request:**
```json
{
    "leaders": [
        {"name": "Alpha", "march_time": 30, "rally_fill_time": 10},
        {"name": "Beta", "march_time": 30, "rally_fill_time": 10},
        {"name": "Gamma", "march_time": 30, "rally_fill_time": 10}
    ],
    "hitting_order": ["Alpha", "Beta", "Gamma"],
    "hit_spacing": 2.0
}
```

**Response:**
```json
{
    "success": true,
    "launch_sequence": [
        {
            "leader_name": "Alpha",
            "launch_time": 0.0,
            "launch_order": 1,
            "hit_time": 30.0,
            "wait_instruction": "Launch immediately"
        },
        {
            "leader_name": "Beta",
            "launch_time": 2.0,
            "launch_order": 2,
            "hit_time": 32.0,
            "wait_instruction": "Wait 2.0s after Alpha launches"
        },
        {
            "leader_name": "Gamma",
            "launch_time": 4.0,
            "launch_order": 3,
            "hit_time": 34.0,
            "wait_instruction": "Wait 2.0s after Beta launches"
        }
    ],
    "summary": "Alpha launches first. Beta waits 2.0s after Alpha, then launches. Gamma waits 2.0s after Beta, then launches.",
    "all_hit_time": 34.0
}
```

---

## Files Changed

| File | Changes |
|------|---------|
| `api/rally_timing_v2.py` | New calculator with simplified logic |
| `api/main.py` | Added `/rally/calculate-v2` endpoint |
| `rally_v2.html` | New simplified UI with How to USE guide |

---

## Key Features

✅ **User-Friendly**: Focus on what matters - launch order and timing  
✅ **No UTC Confusion**: Simple seconds-based timing  
✅ **Clear Instructions**: Each leader knows exactly when to launch  
✅ **Flexible Hit Spacing**: Support simultaneous hits or staggered hits  
✅ **Responsive Design**: Works on mobile and desktop  
✅ **How to USE Guide**: Built-in instructions for new users  

---

## Testing

1. Add 3 leaders (Alpha, Beta, Gamma) with 30s march time
2. Set hitting order: Alpha → Beta → Gamma
3. Set hit spacing: 2 seconds
4. Click Calculate
5. Verify output shows correct launch sequence

Expected output:
- Alpha launches at 0s
- Beta launches at 2s (waits 2s after Alpha)
- Gamma launches at 4s (waits 2s after Beta)
