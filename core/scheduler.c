/* SPDX-License-Identifier: MIT */
#include "scheduler.h"

/* mktime normalizes the local civil calendar; UTC conversions would be wrong
 * around daylight-saving transitions for an overnight local-time schedule. */
static bool prev_calendar_day(const struct tm *local, struct tm *prev) {
    if (!local || !prev) return false;
    *prev = *local;
    prev->tm_mday -= 1;
    prev->tm_hour = 12;    /* midday avoids most DST-transition ambiguity */
    prev->tm_min = 0;
    prev->tm_sec = 0;
    prev->tm_isdst = -1;
    return mktime(prev) != (time_t)-1;
}

bool daily_schedule_valid(const daily_schedule_t *plan) {
    return plan && plan->start_minute < 1440 && plan->end_minute < 1440 &&
           plan->start_minute != plan->end_minute &&
           (plan->weekdays & 0x7f) != 0 && plan->max_starts > 0;
}

bool daily_schedule_active(const daily_schedule_t *plan, const struct tm *local) {
    if (!daily_schedule_valid(plan) || !local || local->tm_wday < 0 ||
        local->tm_wday > 6) return false;
    const int minute = local->tm_hour * 60 + local->tm_min;
    const int start = plan->start_minute, end = plan->end_minute;
    if (start < end) {
        return minute >= start && minute < end &&
               (plan->weekdays & (1U << local->tm_wday)) != 0;
    }
    if (minute >= start)
        return (plan->weekdays & (1U << local->tm_wday)) != 0;
    if (minute < end) {
        struct tm prev;
        if (!prev_calendar_day(local, &prev)) return false;
        return (plan->weekdays & (1U << prev.tm_wday)) != 0;
    }
    return false;
}

int32_t daily_schedule_session_key(const daily_schedule_t *plan,
                                   const struct tm *local) {
    if (!daily_schedule_active(plan, local)) return -1;
    struct tm start_day = *local;
    const int minute = local->tm_hour * 60 + local->tm_min;
    if (plan->start_minute > plan->end_minute && minute < plan->end_minute &&
        !prev_calendar_day(local, &start_day)) return -1;
    /* tm_year is years since 1900, 366 provides collision-free day buckets. */
    return (int32_t)(start_day.tm_year * 366 + start_day.tm_yday);
}

daily_action_t daily_schedule_decide(const daily_schedule_t *plan,
                                     const struct tm *local,
                                     const daily_observation_t *obs) {
    if (!daily_schedule_valid(plan) || !local || !obs ||
        !obs->clock_valid || !obs->camera_connected || !obs->status_fresh)
        return DAILY_HOLD; /* Never act using guessed camera/time state. */
    if (!daily_schedule_active(plan, local)) {
        if (obs->maybe_ours)
            return obs->is_recording ? DAILY_STOP : DAILY_CLEAR_OWNERSHIP;
        return DAILY_HOLD; /* Never stop somebody else's recording. */
    }
    if (obs->is_recording) return DAILY_HOLD;
    if (obs->start_attempts >= plan->max_starts) return DAILY_HOLD;
    if (!obs->is_timelapse) return DAILY_SELECT_TIMELAPSE;
    return DAILY_START;
}
