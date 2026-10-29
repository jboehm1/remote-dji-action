/* SPDX-License-Identifier: MIT */
#ifndef DAILY_TIMELAPSE_SCHEDULER_H
#define DAILY_TIMELAPSE_SCHEDULER_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

/* Bit 0 = Sunday, bit 6 = Saturday. 0x7f means every day. */
typedef struct {
    uint16_t start_minute;  /* 0..1439, local wall clock */
    uint16_t end_minute;    /* 0..1439, must differ from start */
    uint8_t weekdays;      /* start-day weekdays */
    uint8_t max_starts;    /* attempts per window, >= 1 */
} daily_schedule_t;

typedef struct {
    bool clock_valid;
    bool camera_connected;
    bool status_fresh;
    bool is_recording;
    bool is_timelapse;
    bool allow_start;   /* true only when camera temperature/storage checks pass */
    bool maybe_ours;      /* persisted before sending START */
    uint8_t start_attempts;
} daily_observation_t;

typedef enum {
    DAILY_HOLD = 0,
    DAILY_SELECT_TIMELAPSE,
    DAILY_START,
    DAILY_STOP,
    DAILY_CLEAR_OWNERSHIP
} daily_action_t;

bool daily_schedule_valid(const daily_schedule_t *plan);
bool daily_schedule_active(const daily_schedule_t *plan, const struct tm *local);
int32_t daily_schedule_session_key(const daily_schedule_t *plan,
                                   const struct tm *local);
daily_action_t daily_schedule_decide(const daily_schedule_t *plan,
                                     const struct tm *local,
                                     const daily_observation_t *obs);

#endif
