#ifndef DEVICE_CONFIG_H
#define DEVICE_CONFIG_H

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize device configuration from NVS
 *
 * @return esp_err_t ESP_OK on success
 */
esp_err_t device_config_init(void);

/**
 * @brief Get device code (unique identifier)
 *
 * @return const char* Device code string
 */
const char *device_config_get_code(void);

/**
 * @brief Get server URL
 *
 * @return const char* Server URL string
 */
const char *device_config_get_server_url(void);

/**
 * @brief Get Wi-Fi SSID
 *
 * @return const char* Wi-Fi SSID
 */
const char *device_config_get_wifi_ssid(void);

/**
 * @brief Get Wi-Fi password
 *
 * @return const char* Wi-Fi password
 */
const char *device_config_get_wifi_password(void);

/**
 * @brief Set device configuration
 *
 * @param device_code Device code
 * @param server_url Server URL
 * @param wifi_ssid Wi-Fi SSID
 * @param wifi_password Wi-Fi password
 * @return esp_err_t ESP_OK on success
 */
esp_err_t device_config_set(
    const char *device_code,
    const char *server_url,
    const char *wifi_ssid,
    const char *wifi_password
);

#ifdef __cplusplus
}
#endif

#endif // DEVICE_CONFIG_H
