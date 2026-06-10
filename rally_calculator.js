/**
 * Rally Timing Calculator (JavaScript)
 * Simplified rally timing calculations for WOS players
 * 
 * Functions:
 * - parseTimeToMs(timeStr): Convert "m:ss" to milliseconds
 * - formatMsToTime(ms): Convert milliseconds to "m:ss"
 * - calculateRallyTiming(leaders): Calculate launch times and offsets
 * - validateRallyConfig(leaders): Validate input configuration
 */

/**
 * Parse time string (m:ss or mm:ss) to milliseconds
 */
function parseTimeToMs(timeStr) {
  const parts = timeStr.split(":");
  if (parts.length !== 2) throw new Error("Invalid time format. Use m:ss or mm:ss");

  const minutes = parseInt(parts[0], 10);
  const seconds = parseInt(parts[1], 10);

  if (isNaN(minutes) || isNaN(seconds) || seconds >= 60) {
    throw new Error("Invalid time values");
  }

  return minutes * 60 * 1000 + seconds * 1000;
}

/**
 * Format milliseconds to readable time string
 */
function formatMsToTime(ms) {
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Calculate rally timing for all leaders
 * 
 * Input: Array of leaders with:
 * - name: string
 * - marchTimeMs: number (milliseconds)
 * - rallyFillTimeMs: number (milliseconds)
 * - hitOrder: number (1 = first to hit, 2 = second, etc.)
 * 
 * Output: Object with calculations array and summary
 */
function calculateRallyTiming(leaders, targetHitTimeMs = 0) {
  if (leaders.length === 0) {
    throw new Error("At least one leader is required");
  }

  // Sort leaders by hit order
  const sortedLeaders = [...leaders].sort((a, b) => a.hitOrder - b.hitOrder);

  // Calculate hit times based on hit order
  const hitTimes = [];
  const baseHitTime = targetHitTimeMs || 0;

  for (let i = 0; i < sortedLeaders.length; i++) {
    // Each leader hits 0.5 seconds after the previous one
    hitTimes.push(baseHitTime + i * 500);
  }

  // Calculate launch times (hit time - march time - rally fill time)
  const launchTimes = [];
  for (let i = 0; i < sortedLeaders.length; i++) {
    const hitTime = hitTimes[i];
    const launchTime = hitTime - sortedLeaders[i].marchTimeMs - sortedLeaders[i].rallyFillTimeMs;
    launchTimes.push(launchTime);
  }

  // Find the earliest launch time
  const earliestLaunchTime = Math.min(...launchTimes);

  // Calculate offsets from the earliest launch time
  const calculations = [];

  for (let i = 0; i < sortedLeaders.length; i++) {
    const leader = sortedLeaders[i];
    const launchTime = launchTimes[i];
    const hitTime = hitTimes[i];
    const offsetFromFirst = launchTime - earliestLaunchTime;

    // Generate instruction
    let instruction = "";
    if (offsetFromFirst === 0) {
      instruction = `${leader.name} launches FIRST`;
    } else if (offsetFromFirst > 0) {
      const delaySeconds = Math.round(offsetFromFirst / 1000);
      instruction = `${leader.name} waits ${delaySeconds}s, then launches (${formatMsToTime(offsetFromFirst)} after ${sortedLeaders[0].name})`;
    } else {
      instruction = `${leader.name} launches before others (timing conflict)`;
    }

    calculations.push({
      leaderName: leader.name,
      marchTimeMs: leader.marchTimeMs,
      rallyFillTimeMs: leader.rallyFillTimeMs,
      hitOrder: leader.hitOrder,
      launchTimeMs: launchTime,
      launchTimeFormatted: formatMsToTime(Math.max(0, launchTime)),
      hitTimeMs: hitTime,
      hitTimeFormatted: formatMsToTime(hitTime),
      offsetFromFirstMs: offsetFromFirst,
      offsetFromFirstFormatted: formatMsToTime(Math.max(0, offsetFromFirst)),
      instruction,
    });
  }

  // Calculate summary
  const firstHitTime = Math.min(...hitTimes);
  const lastHitTime = Math.max(...hitTimes);
  const totalDuration = lastHitTime - firstHitTime;

  const summary =
    calculations.length === 1
      ? `${calculations[0].leaderName} hits at ${formatMsToTime(firstHitTime)}`
      : `All leaders hit within ${formatMsToTime(totalDuration)} (${calculations.length} rallies)`;

  return {
    calculations,
    firstHitTimeMs: firstHitTime,
    totalDurationMs: totalDuration,
    summary,
  };
}

/**
 * Validate rally timing configuration
 */
function validateRallyConfig(leaders) {
  const errors = [];

  if (leaders.length === 0) {
    errors.push("At least one leader is required");
  }

  if (leaders.length > 5) {
    errors.push("Maximum 5 leaders allowed");
  }

  // Check for duplicate hit orders
  const hitOrders = leaders.map((l) => l.hitOrder);
  if (new Set(hitOrders).size !== hitOrders.length) {
    errors.push("Duplicate hit orders detected");
  }

  // Check for valid hit orders
  for (const leader of leaders) {
    if (leader.hitOrder < 1 || leader.hitOrder > leaders.length) {
      errors.push(`Invalid hit order for ${leader.name}`);
    }
  }

  return errors;
}

// Export for Node.js/CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    parseTimeToMs,
    formatMsToTime,
    calculateRallyTiming,
    validateRallyConfig,
  };
}
