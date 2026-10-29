/* Build: cc -std=c11 -Wall -Wextra -Werror -Icore core/scheduler.c tests/test_scheduler.c -o /tmp/test_schedule */
#include "scheduler.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static struct tm local_at(int year, int month, int day, int hh, int mm) {
    struct tm t = {0};
    t.tm_year = year - 1900;
    t.tm_mon = month - 1;
    t.tm_mday = day;
    t.tm_hour = hh;
    t.tm_min = mm;
    t.tm_isdst = -1;
    assert(mktime(&t) != (time_t)-1);
    return t;
}

int main(void) {
    setenv("TZ", "CET-1CEST,M3.5.0,M10.5.0/3", 1);
    tzset();
    daily_schedule_t d = {.start_minute = 8 * 60, .end_minute = 18 * 60,
                          .weekdays = 0x7f, .max_starts = 3};
    assert(daily_schedule_valid(&d));
    struct tm t = local_at(2026, 10, 29, 7, 59);
    assert(!daily_schedule_active(&d, &t));
    t = local_at(2026, 10, 29, 8, 0);
    assert(daily_schedule_active(&d, &t));
    int32_t this_session = daily_schedule_session_key(&d, &t);
    t = local_at(2026, 10, 29, 17, 59);
    assert(daily_schedule_active(&d, &t));
    assert(daily_schedule_session_key(&d, &t) == this_session);
    t = local_at(2026, 10, 29, 18, 0);
    assert(!daily_schedule_active(&d, &t));

    daily_observation_t o = {.clock_valid = true, .camera_connected = true,
        .status_fresh = true, .is_timelapse = true, .max_starts = 0};
    t = local_at(2026, 10, 29, 8, 0);
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_START);
    o.is_timelapse = false;
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_SELECT_TIMELAPSE);
    o.is_recording = true;
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_HOLD);
    t = local_at(2026, 10, 29, 18, 0);
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_HOLD);
    o.maybe_ours = true;
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_STOP);
    o.is_recording = false;
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_CLEAR_OWNERSHIP);
    o.clock_valid = false;
    assert(daily_schedule_decide(&d, &t, &o) == DAILY_HOLD);

    d.start_minute = 23 * 60;
    d.end_minute = 2 * 60;
    d.weekdays = (1U << 4); /* Thursday start -> Friday after midnight */
    t = local_at(2026, 10, 29, 23, 0);
    assert(daily_schedule_active(&d, &t));
    int32_t session = daily_schedule_session_key(&d, &t);
    t = local_at(2026, 10, 30, 1, 59);
    assert(daily_schedule_active(&d, &t));
    assert(daily_schedule_session_key(&d, &t) == session);
    t = local_at(2026, 10, 30, 2, 0);
    assert(!daily_schedule_active(&d, &t));
    t = local_at(2026, 10, 31, 1, 0);
    assert(!daily_schedule_active(&d, &t));

    d.start_minute = d.end_minute;
    assert(!daily_schedule_valid(&d));
    puts("All daily scheduler tests passed");
    return 0;
}
