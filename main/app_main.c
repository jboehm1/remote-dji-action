/* SPDX-License-Identifier: MIT
 * Experimental daily timelapse scheduler using DJI's own R SDK BLE demo.
 * Not validated on a physical Osmo Action 6: do not use unattended yet.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "esp_err.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_sntp.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "scheduler.h"
#include "ble.h"
#include "data.h"
#include "connect_logic.h"
#include "command_logic.h"
#include "status_logic.h"
#include "enums_logic.h"
#include "dji_protocol_data_structures.h"

static const char *TAG = "DAILY_LAPSE";
static volatile uint32_t last_status_ms = 0;
static volatile uint8_t camera_heat_status = 255;
static volatile uint32_t camera_storage_mb = 0;
static bool maybe_ours = false;
static int32_t attempts_session = -1;
static uint8_t start_attempts = 0;
static uint32_t last_command_ms = 0;

static uint32_t uptime_ms(void) {
    return (uint32_t)(esp_timer_get_time() / 1000ULL);
}

static void status_received(void *data) {
    if (!data) return;
    const camera_status_push_command_frame *state = data;
    camera_heat_status = state->temp_over;
    camera_storage_mb = state->remain_capacity;
    update_camera_state_handler(data);
    last_status_ms = uptime_ms();
}

static void extra_status_received(void *data) {
    update_new_camera_state_handler(data);
}

static void save_state(void) {
    nvs_handle_t handle;
    if (nvs_open("schedule", NVS_READWRITE, &handle) != ESP_OK) return;
    nvs_set_u8(handle, "owner", maybe_ours ? 1 : 0);
    nvs_set_i32(handle, "session", attempts_session);
    nvs_set_u8(handle, "starts", start_attempts);
    esp_err_t err = nvs_commit(handle);
    if (err != ESP_OK) ESP_LOGE(TAG, "NVS persist failed: %s", esp_err_to_name(err));
    nvs_close(handle);
}

static void load_state(void) {
    nvs_handle_t handle;
    if (nvs_open("schedule", NVS_READONLY, &handle) != ESP_OK) return;
    uint8_t owner = 0, starts = 0;
    nvs_get_u8(handle, "owner", &owner);
    nvs_get_i32(handle, "session", &attempts_session);
    nvs_get_u8(handle, "starts", &starts);
    maybe_ours = owner != 0;
    start_attempts = starts;
    nvs_close(handle);
}

static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg; (void)data;
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ESP_LOGI(TAG, "Wi-Fi connected; SNTP available");
    }
}

static void initialize_clock(void) {
    setenv("TZ", CONFIG_DT_TZ, 1);
    tzset();
    if (strlen(CONFIG_DT_WIFI_SSID) == 0) {
        ESP_LOGE(TAG, "No Wi-Fi configured: scheduler will refuse to run without valid time");
        return;
    }
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, wifi_event, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event, NULL));
    wifi_config_t cfg = {0};
    snprintf((char *)cfg.sta.ssid, sizeof(cfg.sta.ssid), "%s", CONFIG_DT_WIFI_SSID);
    snprintf((char *)cfg.sta.password, sizeof(cfg.sta.password), "%s", CONFIG_DT_WIFI_PASSWORD);
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_connect());
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, CONFIG_DT_NTP_SERVER);
    esp_sntp_init();
}

static bool connect_camera(void) {
    if (connect_logic_get_state() == PROTOCOL_CONNECTED) return true;
    /* If the demo reconnected GATT by itself, reestablish application protocol. */
    if (connect_logic_get_state() != BLE_CONNECTED) {
        if (connect_logic_ble_connect(false) != 0) return false;
    }
    uint8_t mac[6] = {0};
    if (esp_read_mac(mac, ESP_MAC_WIFI_STA) != ESP_OK) return false;
    int8_t request_mac[6];
    for (int i = 0; i < 6; ++i) request_mac[i] = (int8_t)mac[i];
    uint32_t device_id = ((uint32_t)mac[2] << 24) | ((uint32_t)mac[3] << 16) |
                         ((uint32_t)mac[4] << 8) | mac[5];
    /* Camera approval may be required on the first pairing. */
    if (connect_logic_protocol_connect(device_id, 6, request_mac, 0, 0, 0, 0) != 0)
        return false;
    if (subscript_camera_status(PUSH_MODE_PERIODIC_WITH_STATE_CHANGE, PUSH_FREQ_2HZ) != 0)
        return false;
    last_status_ms = 0; /* Require a fresh 1D02 after every connect. */
    camera_heat_status = 255;
    camera_storage_mb = 0;
    ESP_LOGI(TAG, "Camera connected; awaiting validated status");
    return true;
}

static bool accepted_record_command(bool start) {
    record_control_response_frame_t *response =
        start ? command_logic_start_record() : command_logic_stop_record();
    if (!response) return false;
    bool ok = response->ret_code == 0;
    free(response);
    return ok;
}

void app_main(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        /* Do NOT erase NVS automatically: it holds ownership and pairing state. */
        ESP_LOGE(TAG, "NVS recovery required; refusing unattended control");
        return;
    }
    ESP_ERROR_CHECK(err);
    load_state();
    daily_schedule_t plan = {
        .start_minute = CONFIG_DT_START_HOUR * 60 + CONFIG_DT_START_MINUTE,
        .end_minute = CONFIG_DT_END_HOUR * 60 + CONFIG_DT_END_MINUTE,
        .weekdays = CONFIG_DT_WEEKDAYS_MASK,
        .max_starts = CONFIG_DT_MAX_STARTS,
    };
    if (!daily_schedule_valid(&plan)) {
        ESP_LOGE(TAG, "Invalid schedule in menuconfig"); return;
    }
    initialize_clock();
    data_init();
    data_register_status_update_callback(status_received);
    data_register_new_status_update_callback(extra_status_received);
    if (connect_logic_ble_init() != 0) {
        ESP_LOGE(TAG, "Bluetooth init failed"); return;
    }

    uint32_t last_connect_attempt = 0;
    uint32_t last_no_time_warning = 0;
    while (true) {
        const uint32_t now_ms = uptime_ms();
        time_t now = time(NULL);
        const bool clock_valid = now >= (time_t)1735689600; /* >= 2025-01-01 */
        if (!clock_valid && now_ms - last_no_time_warning > 30000) {
            ESP_LOGW(TAG, "Clock not synchronized: no automatic commands");
            last_no_time_warning = now_ms;
        }
        if (clock_valid && connect_logic_get_state() != PROTOCOL_CONNECTED &&
            (last_connect_attempt == 0 || now_ms - last_connect_attempt >= 30000)) {
            last_connect_attempt = now_ms;
            connect_camera();  /* BLE+protocol connect may take tens of seconds. */
        }
        struct tm local = {0};
        if (clock_valid) localtime_r(&now, &local);
        int32_t key = clock_valid ? daily_schedule_session_key(&plan, &local) : -1;
        if (key != -1 && key != attempts_session) {
            attempts_session = key;
            start_attempts = 0;
            save_state();
        }

        daily_observation_t obs = {
            .clock_valid = clock_valid,
            .camera_connected = (connect_logic_get_state() == PROTOCOL_CONNECTED),
            .status_fresh = camera_status_initialized && last_status_ms != 0 &&
                            (uint32_t)(now_ms - last_status_ms) < 10000,
            .is_recording = is_camera_recording(),
            .is_timelapse = current_camera_mode == CAMERA_MODE_TIMELAPSE,
            .allow_start = camera_heat_status == 0 && camera_storage_mb >= 1024,
            .maybe_ours = maybe_ours,
            .start_attempts = start_attempts,
        };
        daily_action_t action = daily_schedule_decide(&plan, &local, &obs);
        if (action == DAILY_CLEAR_OWNERSHIP) {
            maybe_ours = false;
            save_state();
        } else if (action != DAILY_HOLD &&
                   (last_command_ms == 0 || now_ms - last_command_ms >= 20000)) {
            last_command_ms = now_ms;
            switch (action) {
                case DAILY_SELECT_TIMELAPSE:
                    /* No automatic switch yet: official demo hardcodes a model
                     * ID in mode-switch request. Avoid switching to wrong mode.
                     * Set Timelapse + infinite duration on camera beforehand. */
                    ESP_LOGW(TAG, "ACTION REQUIRED: camera must be in Timelapse mode");
                    break;
                case DAILY_START: {
                    /* Persist potential ownership BEFORE sending a command, so
                     * a reboot cannot leave an untracked scheduled recording. */
                    maybe_ours = true;
                    ++start_attempts;
                    save_state();
                    bool ok = accepted_record_command(true);
                    ESP_LOGI(TAG, "START request %s; awaiting state confirmation",
                             ok ? "ACKed" : "failed/no ACK");
                    break;
                }
                case DAILY_STOP: {
                    bool ok = accepted_record_command(false);
                    ESP_LOGI(TAG, "STOP request %s; awaiting state confirmation",
                             ok ? "ACKed" : "failed/no ACK");
                    break;
                }
                default: break;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
