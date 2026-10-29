set(DJI "${CMAKE_CURRENT_LIST_DIR}/../vendor/dji-sdk")
idf_component_register(
    SRCS "app_main.c"
         "../core/scheduler.c"
         "${DJI}/utils/crc/custom_crc16.c"
         "${DJI}/utils/crc/custom_crc32.c"
         "${DJI}/protocol/dji_protocol_parser.c"
         "${DJI}/protocol/dji_protocol_data_processor.c"
         "${DJI}/protocol/dji_protocol_data_descriptors.c"
         "${DJI}/protocol/dji_protocol_data_structures.c"
         "${DJI}/ble/ble.c"
         "${DJI}/data/data.c"
         "${DJI}/logic/connect_logic.c"
         "${DJI}/logic/command_logic.c"
         "${DJI}/logic/status_logic.c"
         "${DJI}/logic/enums_logic.c"
    INCLUDE_DIRS "." "../core"
    PRIV_INCLUDE_DIRS "${DJI}/utils/crc" "${DJI}/protocol"
        "${DJI}/ble" "${DJI}/data" "${DJI}/logic"
    PRIV_REQUIRES bt nvs_flash esp_wifi esp_netif esp_event esp_timer
)
